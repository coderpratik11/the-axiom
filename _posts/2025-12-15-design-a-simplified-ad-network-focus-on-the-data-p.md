---
title: "Design a simplified ad network. Focus on the data pipeline that collects impression/click data, processes it, and generates reports for advertisers."
date: 2025-12-15
categories: [System Design, Concepts]
tags: [interview, architecture, learning]
toc: true
layout: post
---

## 1. The Core Concept

Imagine a bustling marketplace where various vendors (advertisers) want to display their products (ads) to potential customers (users) browsing different shops (websites/apps). An ad network acts as the central coordinator, connecting advertisers with publishers and ensuring their ads are shown effectively. But it doesn't stop there – to prove value, the network needs to track exactly how many people *saw* an ad and how many *interacted* with it.

> A **simplified ad network** is a platform that connects advertisers with publishers to display ads. Its **data pipeline** is the crucial backbone responsible for collecting **impression** (ad displayed) and **click** (ad interacted with) data, processing it, and transforming it into valuable, actionable **reports for advertisers**.

This data pipeline is the lifeblood, enabling accurate billing, campaign optimization, and performance analysis. Without it, an ad network is flying blind.

## 2. Deep Dive & Architecture

Designing this pipeline involves several interconnected stages, each optimized for scale, reliability, and speed. We'll focus on the core components for collecting, processing, and storing impression/click data.

### 2.1. Data Collection

This is the initial point where raw events are captured.

*   **Client-Side Tracking:** When an ad is loaded or clicked, a small piece of code (often a **tracking pixel** for impressions or a redirect URL for clicks) sends a request to the ad network's data collection endpoint.
    *   **Impression Tracking:** A 1x1 pixel image request (or similar asynchronous call) is made when an ad is rendered. The request URL contains parameters identifying the ad, publisher, user, and other context.
    *   **Click Tracking:** A user clicking an ad is first redirected through the ad network's click tracking server, which logs the click, and then redirects the user to the advertiser's landing page.
*   **Event Schema:** Each collected event (impression or click) adheres to a predefined schema to ensure consistency.
    json
    {
        "event_id": "uuid_v4",
        "timestamp": "ISO_8601_string",
        "event_type": "impression" | "click",
        "ad_id": "string",
        "campaign_id": "string",
        "advertiser_id": "string",
        "publisher_id": "string",
        "user_id": "hashed_string" | null, // Privacy-focused ID
        "device_type": "mobile" | "desktop",
        "browser": "Chrome",
        "os": "Android",
        "ip_address": "string", // Anonymized or hashed
        "geo_location": "string", // Derived from IP
        "ad_position": "top" | "bottom"
    }
    

### 2.2. Data Ingestion & Queueing

Collected events need to be ingested reliably and at high throughput.

*   **Load Balancers & API Gateways:** Distribute incoming requests to a fleet of ingestion servers.
*   **Event Ingestion Service:** Lightweight, highly available servers whose sole purpose is to validate the incoming event schema, add server-side metadata (e.g., ingestion timestamp), and immediately push the events into a durable message queue.
*   **Message Queue (e.g., Apache Kafka, AWS Kinesis):** Critical for decoupling the collection service from processing services. It acts as a buffer, handling bursts of traffic and ensuring data durability even if downstream processors are temporarily down.
    *   **Pro Tip:** Use multiple topics or streams (e.g., `impressions_raw`, `clicks_raw`) for better organization and independent scaling of processors.

### 2.3. Data Processing

This stage transforms raw events into meaningful data for reporting. This often involves both real-time and batch processing.

#### 2.3.1. Real-time Stream Processing (e.g., Apache Flink, Apache Spark Streaming)

*   **Purpose:** For immediate insights, fraud detection, live dashboards, and rapidly updating aggregate metrics.
*   **Tasks:**
    *   **Filtering & Sampling:** Discarding bot traffic, invalid events.
    *   **Enrichment:** Adding more context (e.g., mapping IP to precise geo-location using a lookup service, joining with user profile data).
    *   **De-duplication:** Identifying and removing duplicate events (especially for impressions where tracking pixels can sometimes fire multiple times).
    *   **Aggregations:** Calculating basic metrics like impressions per minute, clicks per minute for immediate dashboards.
    *   **Anomaly Detection:** Flagging suspicious click patterns or unusually high impression rates.

#### 2.3.2. Batch Processing (e.g., Apache Spark, Hadoop MapReduce)

*   **Purpose:** For complex aggregations, historical analysis, machine learning model training, and generating definitive daily/hourly reports.
*   **Tasks:**
    *   **ETL (Extract, Transform, Load):** Processing large volumes of raw data from long-term storage (e.g., S3) on a scheduled basis (e.g., hourly, daily).
    *   **Complex Aggregations:** Calculating various metrics (CTR, spend, conversions) across different dimensions (campaign, advertiser, publisher, device, geo, time-of-day).
    *   **Data Quality Checks:** More rigorous validation and cleansing.
    *   **Joining Data:** Integrating with other datasets like conversion data from advertisers, bidding data, etc.
    *   **Building Data Models:** Creating optimized tables for querying by reporting tools.

### 2.4. Data Storage

Different types of data require different storage solutions.

*   **Raw Event Storage (Data Lake):**
    *   **Technology:** Cloud object storage (e.g., AWS S3, Google Cloud Storage) or HDFS.
    *   **Purpose:** Store all raw, immutable events for historical analysis, re-processing, and auditing. Highly scalable and cost-effective.
*   **Processed Data Storage (Data Warehouse/OLAP Database):**
    *   **Technology:** Columnar databases optimized for analytical queries (e.g., Amazon Redshift, Google BigQuery, Snowflake, ClickHouse, Apache Druid).
    *   **Purpose:** Store aggregated, denormalized, and structured data ready for reporting. Designed for fast analytical queries across large datasets.
    *   **Example Table Schema (Aggregated Daily Report):**
        sql
        CREATE TABLE daily_ad_performance (
            report_date DATE,
            advertiser_id VARCHAR(50),
            campaign_id VARCHAR(50),
            publisher_id VARCHAR(50),
            geo_location VARCHAR(100),
            device_type VARCHAR(20),
            total_impressions BIGINT,
            total_clicks BIGINT,
            estimated_revenue DECIMAL(10, 4),
            PRIMARY KEY (report_date, advertiser_id, campaign_id, publisher_id, geo_location, device_type)
        );
        
*   **Real-time Dashboards Storage:**
    *   **Technology:** Key-value stores (e.g., Redis) or in-memory databases for rapidly updated, less persistent aggregates.

### 2.5. Reporting & Analytics

The final stage where processed data is presented to advertisers.

*   **Reporting API:** Allows advertisers to programmatically fetch their campaign performance data.
*   **Advertiser Dashboard:** A web-based UI providing visualizations, custom report generation, and drill-down capabilities.
*   **BI Tools:** Internally, data analysts use tools like Tableau, Power BI, Looker, or custom Jupyter notebooks to run ad-hoc queries and generate deeper insights.

mermaid
graph TD
    subgraph Data Collection
        A[User Browser/App] --> B(Tracking Pixel/Redirect);
        B --> C(Load Balancer/API Gateway);
    end

    subgraph Data Ingestion
        C --> D{Event Ingestion Service};
        D --> E[Message Queue (Kafka/Kinesis)];
    end

    subgraph Data Processing
        E --> F[Stream Processor (Flink/Spark Streaming)]
        E --> G[Batch Processor (Spark/Hadoop)];
        F --> H[Real-time Aggregates/Dashboards];
    end

    subgraph Data Storage
        E --> I[Raw Event Storage (S3/HDFS Data Lake)];
        G --> J[Processed Data Storage (Data Warehouse/OLAP DB)];
    end

    subgraph Reporting
        J --> K[Reporting API];
        J --> L[Advertiser Dashboard];
        J --> M[Internal BI Tools];
    end

    H --> L;


## 3. Comparison / Trade-offs

A critical design decision in such data pipelines is the balance between **Real-time Processing** and **Batch Processing**. While often used together, their strengths and weaknesses dictate where each is best applied.

| Feature             | Real-time Processing (e.g., Flink, Kinesis Data Analytics)                                   | Batch Processing (e.g., Spark Batch, Hadoop MapReduce)                                         |
| :------------------ | :------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------- |
| **Latency**         | **Low** (seconds to minutes)                                                                 | **High** (minutes to hours)                                                                    |
| **Data Freshness**  | **High** (data available almost immediately after generation)                                | **Lower** (data is processed in discrete chunks, reflecting past periods)                      |
| **Data Volume**     | Processes continuous streams of data, typically one event at a time or in micro-batches.     | Processes large, bounded datasets in their entirety, typically historical data.                  |
| **Complexity**      | Can be complex to set up and manage, especially for stateful computations.                   | Generally simpler to reason about due to finite data and less strict latency requirements.       |
| **Cost**            | Often higher due to continuous resource allocation and specialized stream engines.           | Can be more cost-effective for large volumes due to elastic, on-demand resource scaling.       |
| **Use Cases**       | Live dashboards, fraud detection, immediate campaign adjustments, anomaly detection.          | Definitive daily/hourly reports, complex aggregations, historical analysis, ML model training, billing. |
| **Error Handling**  | More challenging due to continuous flow; idempotent operations are crucial.                  | Easier to re-process failed batches from a known good state.                                     |
| **Scalability**     | Highly scalable for throughput, but state management can be a bottleneck.                    | Highly scalable for data volume, often easier to scale horizontally.                           |

> **Pro Tip:** For ad networks, a **hybrid approach** is usually best. Real-time streams power operational dashboards and fraud detection, while robust batch processes handle final, auditable reports and billing, ensuring accuracy and data integrity.

## 4. Real-World Use Case

Every major digital advertising platform, from **Google Ads** and **Meta Ads (Facebook/Instagram)** to smaller ad tech companies like **The Trade Desk** and **Magnite**, relies on incredibly sophisticated data pipelines mirroring the principles discussed.

**Why are these pipelines critical?**

1.  **Accurate Billing:** Advertisers pay based on impressions and clicks. The pipeline ensures every billable event is counted precisely, preventing revenue leakage or overcharging. This is paramount for trust and financial stability.
2.  **Performance Optimization:** Real-time data allows advertisers to see how their campaigns are performing *right now*. If an ad isn't generating clicks in a specific region, adjustments can be made immediately, maximizing ROI.
3.  **Fraud Detection:** Ad fraud (e.g., bot clicks, fake impressions) is a multi-billion dollar problem. The data pipeline is the first line of defense, using real-time analysis to detect suspicious patterns and filter out invalid traffic before it impacts billing or campaign metrics.
4.  **Targeting & Personalization:** While not the primary focus of this post, the same pipeline data (user IDs, geo, device, past interactions) is crucial for building user profiles and serving more relevant ads, improving campaign effectiveness.
5.  **Advertiser Insights:** The processed reports provide deep insights into campaign effectiveness, audience demographics, and publisher performance, enabling advertisers to make informed decisions for future strategies.

Without a robust, scalable, and accurate data pipeline, an ad network cannot function effectively, demonstrate value to advertisers, or make informed decisions about its own operations. It's the central nervous system of modern digital advertising.