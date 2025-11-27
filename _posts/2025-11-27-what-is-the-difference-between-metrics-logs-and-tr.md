---
title: "What is the difference between metrics, logs, and traces? Name a popular tool for collecting metrics (e.g., Prometheus) and describe its pull-based architecture."
date: 2025-11-27
categories: [System Design, Concepts]
tags: [interview, architecture, learning, observability, metrics, logs, traces, prometheus]
toc: true
layout: post
---

In the complex landscape of modern software systems, understanding how your applications are performing and diagnosing issues effectively is paramount. This capability is often referred to as **observability**, which relies on collecting and analyzing different types of telemetry data: **metrics**, **logs**, and **traces**. While often discussed together, they each serve distinct purposes and provide unique insights into the health and behavior of your systems.

## 1. The Core Concept

Imagine you're trying to understand the performance and reliability of a brand-new car. To truly grasp its operational state, you wouldn't rely on just one source of information. You'd need a combination of data points, each telling a different part of the story.

> **Observability** is the ability to infer the internal state of a system by examining the data it produces. This data typically falls into three categories: metrics, logs, and traces, often referred to as the "three pillars of observability."

*   **Metrics** are like the car's **dashboard gauges**: a speedometer showing current speed, a fuel gauge indicating fuel level, or an odometer tracking total distance. They provide numerical, aggregatable data points over time, giving you a high-level overview.
*   **Logs** are akin to a **black box flight recorder**: discrete, timestamped events describing what happened at a specific moment. "Engine started," "Brake applied," "Warning: low tire pressure." They offer detailed context for individual occurrences.
*   **Traces** are like following a **single journey from start to finish**: "Driver started engine, drove to gas station, refueled, drove to grocery store, purchased items, drove home." They show the end-to-end path of a request through various components of the system.

## 2. Deep Dive & Architecture

Each pillar of observability offers a different lens through which to view your system's behavior.

### 2.1 Metrics

**Metrics** are numerical measurements collected over time, representing a specific aspect of a system at a particular moment. They are typically aggregated and provide a quantitative view of system health and performance.

*   **Characteristics**:
    *   **Numerical**: Always a number.
    *   **Time-series**: Data points associated with a timestamp.
    *   **Aggregatable**: Easily summed, averaged, counted, or rate-calculated.
    *   **Low Cardinality**: Labels (dimensions) used to categorize metrics are typically limited, making them efficient for storage and querying.
    *   **Ideal for**: Alerting, graphing trends, dashboarding overall system health.

*   **Examples**: CPU utilization, memory usage, request latency, error rates per second, network throughput.

#### Prometheus: A Pull-Based Metrics System

**Prometheus** is a popular open-source monitoring system and time-series database. It's known for its powerful multi-dimensional data model, flexible query language (PromQL), and its distinctive **pull-based architecture**.

**Prometheus's Pull-Based Architecture Explained:**

1.  **Scraping**: Instead of waiting for applications to push metrics, Prometheus actively **pulls** (or "scrapes") metrics from configured targets at regular intervals (e.g., every 15 seconds).
2.  **Targets**: Applications or infrastructure components expose their metrics over HTTP, typically on a dedicated `/metrics` endpoint, in a Prometheus-specific text exposition format.
    *   An application can be directly instrumented with a Prometheus client library (e.g., `promclient` for Python) or use an **exporter**.
    *   **Exporters** are standalone processes that expose metrics for systems that don't natively offer Prometheus format (e.g., `node_exporter` for host OS metrics, `mysqld_exporter` for MySQL metrics).
3.  **Service Discovery**: To dynamically discover targets in a constantly changing environment (like Kubernetes), Prometheus integrates with various service discovery mechanisms (e.g., Kubernetes API, Consul, EC2). This allows it to automatically find and scrape new instances.
4.  **Time-Series Database (TSDB)**: Scraped metrics are stored locally in Prometheus's highly efficient on-disk time-series database.
5.  **PromQL**: Users query the stored metrics using PromQL, a powerful query language for slicing, dicing, and aggregating time-series data.
6.  **Alerting**: Prometheus can be configured with alerting rules based on PromQL queries. When an alert condition is met, Prometheus sends notifications to an **Alertmanager**.
7.  **Visualization**: While Prometheus has a basic UI, it's commonly integrated with **Grafana** for rich, customizable dashboards and visualizations.

yaml
# Example Prometheus configuration snippet for scraping
scrape_configs:
  - job_name: 'prometheus'
    # Scrape Prometheus itself every 5 seconds.
    scrape_interval: 5s
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node_exporter'
    static_configs:
      - targets: ['node1:9100', 'node2:9100'] # node_exporter runs on these hosts


> **Pro Tip**: The pull model simplifies firewall configurations (only Prometheus needs outbound access) and allows Prometheus to enforce scrape intervals and target reliability. It also means the application doesn't need to know where the monitoring system is.

### 2.2 Logs

**Logs** are immutable, timestamped records of discrete events that occurred within a system. They capture detailed textual information about specific actions or occurrences.

*   **Characteristics**:
    *   **Textual/Structured**: Can be plain text or structured (e.g., JSON, key-value pairs).
    *   **Timestamped**: Each entry has a timestamp indicating when the event occurred.
    *   **High Cardinality**: Often contain unique identifiers (e.g., user IDs, transaction IDs) which make them less suitable for direct aggregation without processing.
    *   **Ideal for**: Debugging specific issues, root cause analysis, auditing.

*   **Examples**: "User 'alice' logged in from IP 192.168.1.100", "Database connection failed: Timeout occurred", "Function `process_order` started with ID X123".

*   **Common Tools**: ELK Stack (Elasticsearch, Logstash, Kibana), Splunk, Datadog.

### 2.3 Traces

**Traces** represent the end-to-end journey of a single request or transaction as it propagates through various services and components in a distributed system. They provide visibility into latency and dependencies between services.

*   **Characteristics**:
    *   **Distributed Context**: Links related operations across multiple services using a common `trace_id`.
    *   **Spans**: A trace is composed of ordered operations called **spans**. Each span represents a unit of work within a service (e.g., a database query, an HTTP request to another service).
    *   **Hierarchy**: Spans are often nested, with parent-child relationships, showing the causal flow.
    *   **Ideal for**: Pinpointing performance bottlenecks in distributed systems, understanding service dependencies, visualizing request paths.

*   **Example**: A user clicks a button on a web UI -> `WebUI` calls `AuthService` -> `AuthService` validates credentials -> `AuthService` calls `UserService` -> `UserService` queries `UserDB`. A trace would show the latency of each step and the overall request time.

*   **Common Tools**: Jaeger, Zipkin, OpenTelemetry, Lightstep.

## 3. Comparison / Trade-offs

Understanding when to use each type of telemetry is crucial for effective observability. They are complementary, not interchangeable.

| Feature        | **Metrics**                                 | **Logs**                                         | **Traces**                                    |
|----------------|---------------------------------------------|--------------------------------------------------|-----------------------------------------------|
| **Purpose**    | Quantitative measurement, monitoring trends | Detailed event records for debugging             | End-to-end request flow, latency analysis     |
| **Data Type**  | Numerical, time-series                      | Textual (structured/unstructured events)         | Graph of spans, linked by IDs                 |
| **Granularity**| Aggregated, summarized                      | Fine-grained, individual events                  | Request-specific, multi-service               |
| **Cardinality**| Low (few labels/dimensions)                 | High (many unique values, e.g., user IDs)        | High (per-request unique IDs)                 |
| **Volume**     | Relatively low (due to aggregation)         | Very high (raw event data)                       | Medium to high (often sampled)                |
| **Cost**       | Lower (efficient storage, aggregation)      | Highest (raw data storage, indexing)             | Medium (storage of spans, sampling reduces cost)|
| **Question**   | "What is happening?" (trends, overall health)| "Why did this happen?" (specific error causes)   | "Where is the latency?" (service dependencies)|
| **Example**    | CPU usage `(metric)`, request latency `(metric)` | "User 'alice' logged in `(log)`", "DB connection failed `(log)`" | Request `WebUI` -> `AuthService` -> `UserService` `(trace)` |

## 4. Real-World Use Case

In a typical **microservices architecture**, all three pillars of observability are indispensable. Consider a large-scale e-commerce platform like **Amazon** or **Shopify**:

1.  **Metrics (The "What")**:
    *   Dashboards displaying **overall system health**: "Are our CPU utilization levels within bounds across all services?", "What's the average response time for the checkout service?", "Are our error rates spiking for any particular payment gateway?"
    *   **Alerts**: "If the `InventoryService`'s error rate exceeds 5% for 5 minutes, page the SRE team." Prometheus would be ideal for collecting and alerting on these numerical, time-series data points.

2.  **Logs (The "Why")**:
    *   When an alert fires, or a customer reports an issue, engineers dive into logs.
    *   "A customer's order failed – what specific error message did the `PaymentService` return?"
    *   "Why did the `ProductCatalogService` return an empty result for a valid query?"
    *   Logs provide the detailed, timestamped events that help pinpoint the exact cause of a problem, often containing contextual information like user IDs, request parameters, or stack traces.

3.  **Traces (The "Where")**:
    *   "A customer complained that their shopping cart took 10 seconds to load. Where was the bottleneck?"
    *   A trace would reveal the sequence of service calls: `CartService` -> `RecommendationService` -> `InventoryService` -> `UserService`. It would show that `RecommendationService` took 8 seconds due to a slow database query, identifying the exact culprit in a complex distributed system.
    *   This is critical for understanding performance characteristics and optimizing request paths across hundreds or thousands of interconnected services.

> **Warning**: While all three are crucial, collecting, storing, and analyzing observability data can be expensive. Implement strategies like **sampling** for traces, **structured logging**, and carefully defining **metric cardinality** to manage costs and ensure efficient data processing. Tools like OpenTelemetry aim to standardize instrumentation across these three pillars, making it easier to correlate data.

By effectively leveraging metrics, logs, and traces, engineering teams gain comprehensive visibility into their systems, enabling them to proactively monitor health, quickly diagnose issues, and optimize performance for a seamless user experience.