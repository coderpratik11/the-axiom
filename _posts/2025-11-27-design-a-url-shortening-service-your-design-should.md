---
title: "Design a URL Shortening Service: API, Data Model, and Scalable Key Generation"
date: 2025-11-27
categories: [System Design, Concepts]
tags: [interview, architecture, learning, url-shortener, system-design, distributed-systems, backend]
toc: true
layout: post
---

Designing a URL shortening service is a classic system design interview question and a practical exercise in building a scalable, distributed system. This post will break down the core components, from defining the API to choosing the right data model and, critically, generating unique short keys at scale.

## 1. The Core Concept

Imagine you're at a massive library, and instead of carrying around huge books, you just have a tiny index card that tells you exactly where to find the full book. A URL shortening service works much the same way.

> A **URL shortening service** takes a long, often unwieldy Uniform Resource Locator (URL) and transforms it into a significantly shorter, more memorable, and easier-to-share alias. When the short URL is accessed, the service redirects the user to the original, long URL.

This process involves a mapping between a short identifier (the **short key**) and the original long URL, stored and retrieved efficiently.

## 2. Deep Dive & Architecture

Let's dissect the components required to build such a service.

### 2.1 API Design

The service typically exposes two primary API endpoints: one for creating short URLs and another for redirecting from them.

#### **Creation API**

A `POST` request to create a new short URL.

http
POST /shorten
Content-Type: application/json

{
  "longUrl": "https://www.example.com/very/long/path/to/a/resource/with/many/parameters?param1=value1&param2=value2",
  "customKey": "myAwesomeLink" // Optional: User-defined short key
}


**Response (Success):**
http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "shortUrl": "https://tinydomain.com/abcdeF",
  "longUrl": "https://www.example.com/very/long/path/to/a/resource/with/many/parameters?param1=value1&param2=value2"
}


**Response (Error - e.g., customKey unavailable):**
http
HTTP/1.1 409 Conflict
Content-Type: application/json

{
  "error": "Custom key 'myAwesomeLink' is already in use."
}


#### **Redirection API**

A `GET` request to resolve a short URL and redirect the user.

http
GET /abcdeF


**Response (Success):**
http
HTTP/1.1 302 Found
Location: https://www.example.com/very/long/path/to/a/resource/with/many/parameters?param1=value1&param2=value2


**Response (Error - short key not found):**
http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": "Short URL not found."
}


> **Pro Tip:** For analytical purposes, the redirection endpoint might log details like user agent, IP address, and timestamp before performing the redirect. This data can later be aggregated to provide click analytics.

### 2.2 Data Model

A relational database like **PostgreSQL** or a NoSQL solution like **Cassandra** or **MongoDB** can be used. For simplicity and strong consistency guarantees for the key-URL mapping, a relational database is often a good starting point.

Here's a potential schema for a `short_urls` table:

sql
CREATE TABLE short_urls (
    id BIGSERIAL PRIMARY KEY,           -- Auto-incrementing ID for internal use
    short_key VARCHAR(10) UNIQUE NOT NULL, -- The unique short identifier (e.g., 'abcdeF')
    long_url TEXT NOT NULL,             -- The original URL
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE, -- Optional: For temporary links
    user_id UUID,                       -- Optional: If users can manage their links
    click_count BIGINT DEFAULT 0        -- Optional: For analytics
);

-- Index for efficient lookup by long_url if we want to avoid
-- creating multiple short_keys for the same long_url.
CREATE INDEX idx_long_url ON short_urls (long_url);

-- Index for quick lookup on the short_key, already covered by UNIQUE constraint.
-- CREATE INDEX idx_short_key ON short_urls (short_key);


### 2.3 Key Generation Strategies at Scale

Generating unique, short, and non-predictable keys is the most critical challenge for a URL shortener at scale.

#### **1. Random Hashing with Collision Resolution**

This is a common approach due to its simplicity.

1.  Generate a random string of a fixed length (e.g., 6-8 characters using `[a-zA-Z0-9]`). A 6-character key gives `62^6` (approx. 56 billion) possible combinations.
2.  Check if this randomly generated key already exists in the database.
3.  If it exists (a **collision**), generate another random string and retry.
4.  If it doesn't exist, use it.


function generateRandomKey(length):
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    key = ""
    for _ in range(length):
        key += random.choice(chars)
    return key

function createShortUrl(longUrl):
    key_length = 6
    while True:
        short_key = generateRandomKey(key_length)
        if database.get(short_key) is None:
            database.insert(short_key, longUrl)
            return short_key


> **Warning:** As the number of short URLs grows, the probability of collisions increases. This can lead to frequent database lookups and retries, becoming a performance bottleneck. This strategy is suitable for services with moderate scale.

#### **2. Counter-Based (Base64 Encoding)**

This method guarantees uniqueness and is predictable.

1.  Use a globally unique, monotonically increasing counter. This could be an auto-incrementing `id` from a database, or a dedicated distributed counter service (e.g., using Redis, ZooKeeper).
2.  Encode this counter value into a base (e.g., Base62 or Base64) to get a shorter alphanumeric string.
    *   `1000` (decimal) -> `g8` (Base62)


function encodeBase62(number):
    chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    base = len(chars)
    result = []
    while number > 0:
        result.insert(0, chars[number % base])
        number //= base
    return "".join(result) if result else "0"

function createShortUrl(longUrl):
    next_id = database.get_next_sequence_id() // Globally unique ID
    short_key = encodeBase62(next_id)
    database.insert(short_key, longUrl)
    return short_key


> **Pro Tip:** To make the keys less predictable, you can add a simple transform like a bitwise XOR with a fixed salt, or shuffle the Base62 character set before encoding.

#### **3. Distributed Pre-generated Keys**

This is often the most scalable approach for very high throughput.

1.  A dedicated **Key Generation Service** asynchronously generates large batches of unique short keys.
2.  These keys are stored in a distributed key pool (e.g., a Redis set or a dedicated database table `available_keys`).
3.  When a request to shorten a URL comes in, the URL shortening service picks an available key from the pool.
4.  If the pool runs low, the Key Generation Service is triggered to replenish it.

Key Generation Service can use various methods:
*   **UUIDs (Universally Unique Identifiers):** Generate UUIDs, then take a part of their Base64 representation.
*   **Snowflake ID Generator:** Twitter's Snowflake algorithm generates unique, time-ordered 64-bit IDs in a distributed system. These can then be Base62 encoded.
*   **Hashing with Salting:** Hash the long URL + a random salt + a timestamp, then take a prefix of the hash. Collision checks are still needed but less frequent if enough entropy is in the salt/timestamp.


-- Table for pre-generated keys
CREATE TABLE available_keys (
    key VARCHAR(10) PRIMARY KEY,
    is_used BOOLEAN DEFAULT FALSE
);

-- Key Generation Service process:
-- 1. Generate N keys using Snowflake, UUID, or other method.
-- 2. Insert into `available_keys` (ensuring uniqueness).

-- URL Shortening Service process:
function createShortUrl(longUrl):
    // Atomically fetch and mark a key as used
    short_key = database.get_and_mark_used_key_from_pool()
    if short_key is None:
        // Trigger key generation or retry
        throw Exception("No available keys")

    database.insert(short_key, longUrl)
    return short_key


This decouples key generation from key usage, minimizing latency for the URL shortening request.

## 3. Comparison / Trade-offs

Choosing a key generation strategy involves understanding their respective strengths and weaknesses:

| Feature / Strategy | Random Hashing with Retry | Counter-Based (Base62 Encoding) | Distributed Pre-generated Keys |
| :----------------- | :------------------------ | :------------------------------ | :----------------------------- |
| **Collision Risk** | High (requires retries)   | Very Low (if counter unique)    | Very Low (if generator unique) |
| **Key Predictability** | Low (appears random)      | High (monotonically increasing) | Low (appears random)           |
| **Scalability**    | Moderate (collision checks become bottleneck at scale) | Moderate (centralized counter is a bottleneck) | High (decoupled key generation) |
| **Implementation Complexity** | Low                       | Moderate                        | High                           |
| **Key Length Control** | Easy (fixed length)       | Varies (grows with count, but can cap at 6-8 chars) | Easy (fixed length)            |
| **Performance**    | Degrades under load       | Good for writes, but limited by counter | Excellent (keys are pre-fetched) |

## 4. Real-World Use Cases

URL shortening services are ubiquitous and crucial for various applications:

1.  **Marketing and Analytics:** Services like Bitly, TinyURL, and formerly Goo.gl are heavily used in marketing campaigns. They allow marketers to track **click-through rates (CTR)**, geographical origins of clicks, referral sources, and even device types. This data is invaluable for optimizing campaigns and understanding user engagement.
2.  **Social Media and Messaging:** Platforms with character limits (like older Twitter versions, SMS messages) greatly benefit from short URLs, enabling users to share links without consuming excessive characters.
3.  **Usability and Readability:** Long, complex URLs with many parameters are cumbersome to read, type, and remember. Short URLs enhance user experience by simplifying these links.
4.  **Branding:** Many organizations use custom short domains (e.g., `nyti.ms` for The New York Times, `on.wsj.com` for The Wall Street Journal). This not only shortens URLs but also reinforces brand identity and trust.
5.  **QR Codes:** Shorter URLs result in simpler, denser QR codes that are easier to scan and less prone to errors.
6.  **URL Obfuscation:** While not a security measure, short URLs can hide the complexity and sometimes the nature of the original URL, which can be useful in certain contexts.

By understanding the API, data model, and the nuances of key generation, one can design a robust and scalable URL shortening service capable of handling billions of links.