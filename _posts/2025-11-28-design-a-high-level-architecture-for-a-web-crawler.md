---
title: "Design a high-level architecture for a web crawler. How would you handle politeness (robots.txt), avoid duplicate URLs, and store the vast amount of data collected?"
date: 2025-11-28
categories: [System Design, Concepts]
tags: [interview, architecture, learning]
toc: true
layout: post
---

## 1. The Core Concept

Imagine a tireless, automated librarian whose job is to scour every single book in the world's largest library (the internet), read each one, understand its contents, note down all cross-references to other books, and then meticulously catalog everything into a massive database. This "librarian" is essentially a **web crawler**.

> A **web crawler**, also known as a web spider, robot, or indexer, is an internet bot that systematically browses the World Wide Web, typically for the purpose of Web indexing (for search engines) or data mining.

Its primary goal is to discover new or updated web pages and feed them into a processing pipeline for various applications, such as search engines, data analysis, or archival purposes. The scale of the web makes this a significant system design challenge, requiring careful consideration of distributed systems, data storage, and ethical considerations.

## 2. Deep Dive & Architecture

Designing a robust web crawler requires a modular, distributed architecture to handle the vastness and dynamic nature of the internet. Here’s a high-level overview of the key components and their interactions:

### 2.1. High-Level Architecture Components

The architecture typically consists of several decoupled services:

*   **URL Frontier/Queue**: This is the heart of the crawler, maintaining a prioritized list of URLs to be crawled. It ensures that the most important or freshest URLs are processed first. Common implementations use distributed queues like Apache Kafka, RabbitMQ, or a custom priority queue backed by a database.
*   **DNS Resolver**: Before fetching, URLs need to be resolved to IP addresses. A distributed, caching DNS resolver helps minimize latency and DNS lookup failures.
*   **Robots.txt Handler**: This module is responsible for fetching, parsing, and caching `robots.txt` files for each domain to ensure politeness and adhere to website owners' crawling directives.
*   **Fetcher/Downloader**: This component makes HTTP/HTTPS requests to retrieve the content of web pages. It should handle retries, timeouts, and various HTTP response codes (e.g., redirects, errors). Fetchers are often distributed across many machines to achieve high throughput.
*   **Parser**: Once content is downloaded, the parser extracts relevant information: text, links (hyperlinks), metadata (title, description), and other structured data. Common parsing libraries include Jsoup (Java), BeautifulSoup (Python), or custom HTML/XML parsers.
*   **Deduplicator**: This module prevents the crawler from processing the same URL or the same content multiple times, saving bandwidth, storage, and processing power.
*   **Link Extractor**: A sub-component of the parser that specifically identifies and normalizes outgoing links from the crawled page. These new links are then fed back into the URL Frontier.
*   **Data Storage**: Stores the collected web pages, metadata, and extracted data. This often involves various types of databases.

### 2.2. Handling Politeness (robots.txt)

Web crawling politeness is paramount. Disregarding `robots.txt` or excessively hammering a server can lead to IP bans, legal action, and ethical breaches.

1.  **`robots.txt` Fetching and Parsing**:
    *   Before crawling any URL from a new domain, the crawler *must* fetch the `robots.txt` file located at the root of that domain (e.g., `https://example.com/robots.txt`).
    *   This file specifies rules for different user-agents (crawlers) regarding which paths they are allowed or disallowed to access, and often includes a `Crawl-delay` directive.
    *   Example `robots.txt` entry:
        
        User-agent: MyCrawler
        Disallow: /private/
        Disallow: /admin/
        Crawl-delay: 10
        
        This tells a crawler named `MyCrawler` not to access `/private/` or `/admin/` directories and to wait 10 seconds between requests to this domain.
2.  **Caching Rules**:
    *   `robots.txt` files should be fetched once per domain and **cached** in memory or a distributed cache (e.g., Redis).
    *   The cache should have an expiration policy (e.g., 24 hours) to pick up updated rules.
3.  **Enforcing Rules**:
    *   For every URL retrieved from the URL Frontier, the Robots.txt Handler checks the cached rules for the target domain.
    *   If a URL is disallowed, it's discarded without being fetched.
4.  **Crawl Delay**:
    *   The `Crawl-delay` directive is crucial for preventing server overload. For domains specifying a delay, the Fetcher *must* introduce a pause between consecutive requests to that specific domain. This requires per-domain rate limiting.

> **Pro Tip:** Implement a global rate limiter per IP address or domain to prevent accidentally overwhelming a server, even if `robots.txt` doesn't specify a `Crawl-delay`. This acts as a safety net.

### 2.3. Avoiding Duplicate URLs

Duplicate URLs are a major efficiency killer. A robust crawler must identify and prevent reprocessing the same content.

1.  **URL Normalization**:
    *   URLs can have many forms that point to the same resource. Before storing or checking for duplicates, URLs should be normalized.
    *   This involves:
        *   Converting scheme and host to lowercase (`HTTP://example.com` -> `http://example.com`).
        *   Removing default ports (`:80`, `:443`).
        *   Removing trailing slashes (`/path/` -> `/path`).
        *   Sorting query parameters (`?b=2&a=1` -> `?a=1&b=2`).
        *   Removing `.` and `..` segments.
    *   Example:
        python
        from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

        def normalize_url(url):
            parsed = urlparse(url)
            # Scheme and netloc to lowercase
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            path = parsed.path
            
            # Remove default ports
            if ':' in netloc:
                host, port = netloc.rsplit(':', 1)
                if (scheme == 'http' and port == '80') or \
                   (scheme == 'https' and port == '443'):
                    netloc = host

            # Remove trailing slash from path if not root
            if path.endswith('/') and len(path) > 1:
                path = path[:-1]

            # Sort query parameters
            query_params = parse_qs(parsed.query)
            sorted_query = urlencode(sorted(query_params.items(), key=lambda x: x[0]), doseq=True)

            return urlunparse((scheme, netloc, path, parsed.params, sorted_query, parsed.fragment))

        # Example usage:
        # print(normalize_url("HTTP://Example.COM:80/path/?b=2&a=1#fragment")) 
        # Output: http://example.com/path?a=1&b=2#fragment
        
2.  **Distributed Deduplication Store**:
    *   A high-throughput, low-latency data structure is needed to store all previously seen (normalized) URLs.
    *   **Bloom filters** are excellent for this. They are probabilistic data structures that can efficiently tell you if an element *might* be in a set (with a small chance of false positives) or is *definitely not* in the set. They save significant memory compared to a hash set for very large collections.
    *   For absolute certainty or a smaller set, a **distributed hash set** (e.g., using Redis, Apache Cassandra as a key-value store, or a custom distributed hash table) can store hash values of URLs.
    *   When a new URL is generated, its normalized form's hash is checked against this store. If it exists, it's a duplicate and is discarded. If not, it's added to the store and then to the URL Frontier.

### 2.4. Storing the Vast Amount of Data Collected

The data collected can be enormous, requiring a scalable storage solution.

1.  **What to Store**:
    *   **Raw Content**: The full HTML, XML, or binary content of the fetched page.
    *   **Metadata**: URL, fetch timestamp, HTTP headers (content-type, last-modified), status code, checksum/hash of content.
    *   **Extracted Data**: Title, description, keywords, outgoing links, specific data fields extracted (e.g., product prices, news articles).
    *   **Graph Data**: The link structure of the web (who links to whom).

2.  **Storage Solutions**:
    *   **Raw Content**:
        *   **Distributed File Systems (DFS)**: HDFS (Hadoop Distributed File System) or S3-compatible object storage are ideal for storing raw HTML files due to their high scalability and fault tolerance. Each file can be named by a hash of its URL or content.
        *   **NoSQL Document Databases**: MongoDB or Couchbase can store each page as a document, including raw content and metadata.
        *   **NoSQL Wide-Column Stores**: Apache Cassandra or HBase are suitable for storing large volumes of unstructured data, where the URL can be the row key, and columns store various attributes.
    *   **Metadata and Extracted Data**:
        *   **NoSQL Databases**: As mentioned above, for flexibility and scale.
        *   **Relational Databases (SQL)**: PostgreSQL or MySQL can be used for highly structured metadata or specific extracted data that requires complex querying and strong consistency, particularly if the schema is relatively stable. However, sharding would be necessary for vast scales.
    *   **Link Graph**:
        *   **Graph Databases**: Neo4j or Amazon Neptune are specialized for storing and querying relationships, making them excellent for analyzing the web's link structure.

> **Warning:** Consider data retention policies. Storing every version of every page indefinitely can be prohibitively expensive. Implement strategies for archiving or discarding old content.

## 3. Comparison / Trade-offs

Choosing the right storage solution for crawled data is critical. Here's a comparison of SQL vs. NoSQL databases, specifically for storing the *content* and *metadata* of crawled pages:

| Feature           | Relational Databases (SQL)                               | NoSQL Databases (e.g., Cassandra, MongoDB, HBase)              |
| :---------------- | :------------------------------------------------------- | :------------------------------------------------------------ |
| **Schema**        | **Strict, fixed schema**; data must conform.             | **Flexible, dynamic schema**; ideal for unstructured/semi-structured data. |
| **Scalability**   | **Vertical scaling** (more powerful server). Horizontal scaling (sharding) is complex. | **Horizontal scaling** (adding more servers) is inherent and easier. |
| **Data Model**    | Tables with rows and columns; relationships via foreign keys. | Key-value, document, wide-column, graph. Varied models for different needs. |
| **Consistency**   | **Strong consistency (ACID)**; ensures data integrity.   | **Eventual consistency** often preferred for performance and availability ( tunable). |
| **Querying**      | **SQL** is powerful for complex joins and analytical queries. | API-driven, often simpler queries; less suited for complex joins across diverse datasets. |
| **Use Cases**     | Structured data, financial transactions, clear relationships. | Big data, real-time web, unstructured logs, high-velocity data ingestion. |
| **Web Crawler Fit** | Good for structured metadata, small-scale archives. Can struggle with raw content or vast, evolving schemas. | **Excellent** for storing raw page content, diverse metadata, and large volumes of data. Flexible enough for evolving data extraction needs. |

## 4. Real-World Use Case

The most prominent real-world use case for a web crawler is, without a doubt, **search engines** like Google, Bing, and DuckDuckGo.

**Why Search Engines Rely on Crawlers:**

*   **Discovery**: Search engines constantly need to discover new web pages and updates to existing ones to keep their indexes fresh and comprehensive. Crawlers are the front line of this discovery process.
*   **Indexing**: The data collected by crawlers (page content, links, metadata) is fed into the search engine's indexing pipeline. The index allows search engines to quickly retrieve relevant pages when a user submits a query.
*   **Ranking**: Crawlers help build the "link graph" of the internet. By analyzing which pages link to which others, search engines can determine the authority and relevance of pages, a crucial factor in ranking search results (e.g., Google's PageRank algorithm).
*   **Content Freshness**: The web is constantly changing. News articles are published, products go in and out of stock, and information is updated. Crawlers revisit pages regularly to ensure the search index reflects the most current state of the web.
*   **Data for Other Services**: Beyond core search, the data collected by crawlers is often used for other services, such as Google News, Google Images, or even training AI models.

Without sophisticated web crawling architectures, the internet as we know it—where information is readily discoverable via search—simply wouldn't exist. It's a foundational technology that powers much of our digital interaction.