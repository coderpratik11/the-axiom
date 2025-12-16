---
title: "Revisit the Rate Limiter Design: Building a Distributed Rate Limiter with Redis for API Gateways"
date: 2025-12-16
categories: [System Design, Distributed Systems]
tags: [rate-limiter, redis, distributed-systems, api-gateway, system-design, scalability, performance]
toc: true
layout: post
---

As Principal Software Engineers, we often grapple with challenges of scale, reliability, and security. One fundamental component in achieving these goals, especially for public-facing APIs, is the **rate limiter**. In this post, we'll revisit its core design, focusing on building a distributed rate limiter shared across multiple API gateway instances, and explore how Redis can provide the low-latency storage needed for this critical component.

## 1. The Core Concept

Imagine a popular concert venue. To ensure everyone has a good experience, the venue might limit how many people can enter per minute, or how many tickets one person can buy. This prevents stampedes, ensures safety, and makes sure resources (like staff and space) aren't overwhelmed.

> A **rate limiter** is a system component that controls the rate at which a user, application, or system can access a resource or perform an action within a defined time window. Its primary purpose is to protect services from abuse, prevent resource starvation, and enforce fair usage policies.

In the context of APIs, rate limiters protect our backend services from:
*   **Denial-of-Service (DoS) attacks:** Malicious actors flooding requests.
*   **Resource exhaustion:** A single client monopolizing server resources.
*   **Cost overruns:** Preventing excessive usage that incurs high infrastructure costs.
*   **Fair usage:** Ensuring all legitimate users get a reasonable share of resources.

## 2. Deep Dive & Architecture

Designing a rate limiter for a single server is straightforward. The real challenge emerges when you have multiple API gateway instances, potentially across different data centers, needing to enforce a consistent rate limit policy. This requires a **distributed rate limiter**.

### 2.1. Key Design Considerations for Distributed Rate Limiting

1.  **Consistency:** All gateway instances must agree on the current count for a given user or API key.
2.  **Low Latency:** Checking the rate limit should not add significant overhead to each API call.
3.  **High Availability:** The rate limiter itself should not be a single point of failure.
4.  **Scalability:** The system must handle a growing number of users and requests.
5.  **Granularity:** Ability to define limits per user, API key, IP address, endpoint, or a combination.
6.  **Edge Cases:** Handling clock skew in distributed systems, race conditions during count updates.

### 2.2. Distributed Rate Limiting Architecture with Redis

A typical distributed rate limiting setup involves:

*   **API Gateway Instances:** These are the entry points for client requests. Each instance needs to check the rate limit before proxying the request to the backend service.
*   **Centralized Data Store (Redis):** A shared, highly performant data store where all gateway instances can read and write rate limit counts. Redis is an excellent choice due to its in-memory nature, single-threaded architecture (avoiding race conditions for individual commands), and atomic operations.
*   **Backend Services:** The actual services that fulfill the API requests, protected by the gateway.

mermaid
graph TD
    A[Client] --> B(API Gateway Instance 1)
    A --> C(API Gateway Instance 2)
    A --> D(API Gateway Instance N)

    B -- Check Limit --> E(Redis Cluster)
    C -- Check Limit --> E
    D -- Check Limit --> E

    E -- Result --> B
    E -- Result --> C
    E -- Result --> D

    B -- Forward Request --> F[Backend Service]
    C -- Forward Request --> F
    D -- Forward Request --> F


### 2.3. Rate Limiting Algorithms and Redis Implementation

Let's look at how common rate limiting algorithms can be implemented using Redis to store counts.

#### a. Fixed Window Counter

This is the simplest approach. It defines a fixed time window (e.g., 60 seconds) and allows a maximum number of requests within that window.

*   **How it works:** All requests within a window (e.g., 00:00:00 to 00:00:59) are counted. Once the window ends, the counter resets.
*   **Redis Implementation:**
    *   Use a Redis `string` key for each user/IP, suffixed with the current window's start timestamp.
    *   When a request comes in:
        1.  `KEY = "rate_limit:{user_id}:{window_start_timestamp}"`
        2.  `current_count = INCR KEY`
        3.  If `current_count == 1`, set `EXPIRE KEY {window_duration_seconds}` to automatically delete the key when the window ends.
        4.  Check `current_count` against the limit.

    redis
    # Example: User 123, limit 100 requests per 60 seconds
    # Current timestamp: 1704067200 (start of window)
    
    # On first request in window:
    # Set the expiry time to match the window duration
    EVAL "local current = redis.call('INCR', KEYS[1]); if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end; return current;" 1 "rate_limit:user:123:1704067200" 60
    # Returns 1
    
    # On subsequent requests:
    INCR "rate_limit:user:123:1704067200"
    # Returns 2, 3, ...
    

    > **Pro Tip:** Use `EVAL` with Lua scripts for atomic operations in Redis, especially when combining `INCR` and `EXPIRE` or more complex logic. This prevents race conditions that could occur if multiple commands were sent sequentially.

#### b. Sliding Window Counter

This algorithm addresses the "burstiness" issue of the Fixed Window where a user can make `N` requests at the very end of one window and `N` requests at the very beginning of the next, effectively making `2N` requests in a short period.

*   **How it works:** It combines counts from the current window and the previous window, weighted by how much of the previous window has passed.
*   **Redis Implementation:**
    *   Maintain two fixed windows: the current one and the previous one.
    *   `current_window_key = "rate_limit:{user_id}:{current_window_timestamp}"`
    *   `previous_window_key = "rate_limit:{user_id}:{previous_window_timestamp}"`
    *   When a request comes in:
        1.  Get `current_count` for `current_window_key` (using `INCR` as above).
        2.  Get `previous_count` for `previous_window_key` (using `GET`).
        3.  Calculate `weighted_previous_count = previous_count * (percentage_of_previous_window_elapsed_in_current_window)`.
        4.  `total_count = current_count + weighted_previous_count`.
        5.  Check `total_count` against the limit.

    redis
    # Lua script for Sliding Window Counter (simplified for explanation)
    -- KEYS[1]: current_window_key
    -- KEYS[2]: previous_window_key
    -- ARGV[1]: window_duration_seconds
    -- ARGV[2]: limit
    -- ARGV[3]: current_timestamp (for percentage calculation)
    -- ARGV[4]: window_start_timestamp (for current window)
    -- ARGV[5]: previous_window_start_timestamp
    
    local current_count = redis.call('INCR', KEYS[1]);
    if current_count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end;
    
    local previous_count_str = redis.call('GET', KEYS[2]);
    local previous_count = 0;
    if previous_count_str then previous_count = tonumber(previous_count_str); end;
    
    -- Calculate percentage of previous window remaining
    local time_elapsed_in_current_window = ARGV[3] - ARGV[4];
    local percentage_previous_window_used = 1 - (time_elapsed_in_current_window / tonumber(ARGV[1]));
    if percentage_previous_window_used < 0 then percentage_previous_window_used = 0; end;
    
    local total_count = current_count + (previous_count * percentage_previous_window_used);
    
    if total_count > tonumber(ARGV[2]) then
        return 0 -- Rate limited
    else
        return 1 -- Allowed
    end;
    

#### c. Token Bucket

This algorithm uses a "bucket" that holds a fixed number of tokens. Tokens are added to the bucket at a constant rate. Each request consumes one token. If the bucket is empty, the request is rate-limited.

*   **How it works:** It's good for handling bursts but also for smoothing out request rates over time.
*   **Redis Implementation:**
    *   Store `tokens_in_bucket` and `last_refill_timestamp` in a Redis `HASH` for each user.
    *   When a request comes in:
        1.  Get `tokens_in_bucket` and `last_refill_timestamp`.
        2.  Calculate how many tokens should have been added since `last_refill_timestamp` based on the refill rate.
        3.  Update `tokens_in_bucket` (cap at max bucket size).
        4.  If `tokens_in_bucket >= 1`, decrement it and allow the request. Update `last_refill_timestamp`.
        5.  Else, deny the request.

    redis
    # Lua script for Token Bucket (atomic operations are critical here)
    -- KEYS[1]: user_id (e.g., "token_bucket:user:123")
    -- ARGV[1]: capacity (max tokens)
    -- ARGV[2]: refill_rate (tokens per second)
    -- ARGV[3]: current_timestamp (in seconds)
    
    local bucket = redis.call('HGETALL', KEYS[1]);
    local current_tokens = tonumber(bucket[2]) or ARGV[1]; -- Default to full bucket
    local last_refill_time = tonumber(bucket[4]) or 0;
    
    local fill_time = tonumber(ARGV[3]);
    local capacity = tonumber(ARGV[1]);
    local refill_rate = tonumber(ARGV[2]);
    
    -- Calculate tokens to add
    local time_passed = fill_time - last_refill_time;
    local tokens_to_add = time_passed * refill_rate;
    
    current_tokens = math.min(capacity, current_tokens + tokens_to_add);
    
    if current_tokens >= 1 then
        current_tokens = current_tokens - 1;
        redis.call('HMSET', KEYS[1], "tokens", current_tokens, "last_refill_time", fill_time);
        return 1; -- Allowed
    else
        redis.call('HMSET', KEYS[1], "tokens", current_tokens, "last_refill_time", fill_time); -- Update even if denied
        return 0; -- Denied
    end;
    

### 2.4. Redis Architecture for High Availability and Scale

For a production-grade distributed rate limiter, a single Redis instance is not enough. You'll need:

*   **Redis Cluster:** For sharding data across multiple Redis nodes, providing both horizontal scalability and high availability through master-replica setups within each shard. This ensures that even if one node fails, its replicas can take over.
*   **Sentinel:** If not using a full cluster, Redis Sentinel can be used to monitor master instances, perform automatic failover if a master goes down, and provide configuration to clients.

## 3. Comparison / Trade-offs of Rate Limiting Algorithms

Choosing the right algorithm depends on the specific requirements for fairness, burst handling, and complexity.

| Algorithm               | Pros                                                              | Cons                                                                                                    | Best Use Case                                                                                                    |
| :---------------------- | :---------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------------------------- |
| **Fixed Window Counter**  | - Simple to implement and understand. <br>- Low CPU/memory overhead. | - Allows "bursts" at window edges (e.g., 2N requests at `t-epsilon` and `t+epsilon`).                   | - Simple APIs where occasional bursts are acceptable. <br>- Internal services with predictable traffic.         |
| **Sliding Window Log**    | - Most accurate and "fair" (no edge problem).                     | - High memory usage (stores timestamp for every request). <br>- Slower due to `ZADD` and `ZREMRANGEBYSCORE`. | - Critical APIs requiring precise rate limiting. <br>- When strict fairness and no bursts are paramount.       |
| **Sliding Window Counter**| - Mitigates the "edge problem" of Fixed Window. <br>- Moderate complexity and resource usage. | - Still an approximation, not perfectly accurate as Sliding Window Log.                                 | - Most common choice for general-purpose API rate limiting. <br>- Good balance between accuracy and performance. |
| **Token Bucket**          | - Allows for bursts up to bucket capacity. <br>- Smooths out request rate over time. | - More complex to implement than fixed/sliding window. <br>- Requires careful tuning of capacity and refill rate. | - APIs that need to allow controlled bursts (e.g., occasional batch processing). <br>- Services with varying traffic patterns. |
| **Leaky Bucket**          | - Enforces a perfectly constant output rate.                       | - Can't handle bursts; requests are either queued or dropped. <br>- Can lead to high latency if queue fills up. | - Scenarios where a constant processing rate is critical (e.g., resource-intensive tasks, stream processing). |

> **Warning:** While the Sliding Window Log is the most accurate, its Redis implementation with `ZSET`s (`ZADD` for each request and `ZREMRANGEBYSCORE` to clean old entries) can be very resource-intensive for high-throughput APIs due to constant writes and deletions. Use it judiciously.

## 4. Real-World Use Case

Distributed rate limiters are ubiquitous in modern system architectures:

*   **API Gateways (e.g., AWS API Gateway, Azure API Management, Kong, Apigee):** These are perhaps the most common users. They protect backend microservices, apply usage policies, and provide analytics on API consumption. Without a distributed rate limiter, a client could bypass limits by routing requests through different gateway instances.
*   **Cloud Providers:** Limiting calls to cloud APIs (e.g., number of S3 PUTs per second, EC2 instance launches). This prevents a single customer from consuming excessive shared infrastructure resources.
*   **Payment Gateways:** Limiting transaction requests to prevent fraud or system overload during peak times.
*   **Social Media Platforms:** Restricting how many posts a user can make, how many likes they can give, or how many messages they can send to prevent spam and abuse.
*   **Search Engines:** Limiting query rates from specific IPs to prevent automated scraping.

The "Why" is always about **resource protection** and **fair resource allocation**. In a distributed environment, resources are shared, and system stability depends on preventing any single entity from monopolizing those resources. Redis, with its speed, atomic operations, and robust cluster capabilities, serves as an ideal foundation for building such a critical, low-latency shared state component.