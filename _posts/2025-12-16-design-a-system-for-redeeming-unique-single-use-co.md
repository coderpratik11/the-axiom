---
title: "Design a system for redeeming unique, single-use coupon codes. How do you prevent the same code from being used twice in a high-concurrency scenario? How do you generate millions of unique codes?"
date: 2025-12-16
categories: [System Design, Coupon Systems]
tags: [interview, architecture, systemdesign, distributedsystems, concurrency, couponcodes, database, redis]
toc: true
layout: post
---

## 1. The Core Concept

Imagine a bustling concert venue selling tickets. Each ticket has a unique barcode, and once scanned at the entrance, it's marked as used. If someone tries to re-enter with the same ticket, it's rejected. Our goal with digital coupon codes is precisely this: to ensure each unique code is used **exactly once**, even when thousands of users might try to redeem codes simultaneously.

> A **single-use coupon code system** is designed to generate unique identifiers (codes) that, once redeemed, become invalid for any subsequent use. The system must guarantee atomicity and uniqueness under high-concurrency loads to prevent fraud and ensure fair usage.

This seemingly simple requirement underpins a critical piece of infrastructure for e-commerce, marketing campaigns, and loyalty programs.

## 2. Deep Dive & Architecture

Designing such a system involves two primary challenges: generating a massive volume of unique codes and ensuring their atomic, single-use redemption in a highly concurrent environment.

### 2.1 Generating Millions of Unique Codes

Generating millions of unique codes requires a strategy that balances uniqueness, length, readability, and security.

#### Code Generation Strategies:

1.  **Sequential with Hash/Obfuscation:**
    *   Generate a simple sequential number (e.g., 1, 2, 3...).
    *   Apply a reversible or irreversible transformation (e.g., base62 encoding, a custom scrambling algorithm, or a cryptographic hash like MD5/SHA256 truncated to a desired length).
    *   This ensures uniqueness by design and makes codes harder to guess.
    *   Example: `generate_code(id) = base62_encode(id)` or `generate_code(id) = truncate(sha256(id + salt))`.

2.  **Random Alphanumeric (UUID-like):**
    *   Generate a random string of a specified length using a defined character set (e.g., `A-Z`, `0-9`).
    *   This is simpler and inherently distributed.
    *   **Collision probability** must be considered. For a code length `L` and character set size `C`, the probability of collision increases with the number of generated codes. A sufficient length (e.g., 8-12 characters for alphanumeric) usually makes collisions statistically improbable for millions of codes.
    *   Example: `generate_code() = random_string(length=10, charset='ABCDEFGHJKLMNPQRSTUVWXYZ23456789')`.

#### Considerations for Generation:

*   **Pre-generation vs. On-demand:** For millions of codes, **pre-generation** is often preferred. Codes are generated in batches and stored in a database (or a dedicated code store) with an initial status of `available`. This avoids latency during redemption.
*   **Character Set:** Limit characters to avoid confusion (e.g., `0` vs `O`, `1` vs `L`, `I`). Avoid ambiguous characters.
*   **Length:** Longer codes are more secure (harder to guess) but less user-friendly. A balance (e.g., 8-12 characters) is typically found.
*   **Uniqueness Guarantee:** For random generation, store codes and check for existence before marking as unique. For sequential methods, uniqueness is inherent.
*   **Storage:** A dedicated database table is essential:
    sql
    CREATE TABLE coupon_codes (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        code VARCHAR(12) UNIQUE NOT NULL,
        status ENUM('available', 'redeemed', 'expired', 'pending') NOT NULL DEFAULT 'available',
        campaign_id INT NOT NULL,
        redeemed_by_user_id BIGINT,
        redeemed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    );
    
    An index on `code` and `status` is crucial for fast lookups.

### 2.2 Preventing Double-Use in High-Concurrency

This is the most critical aspect, addressing race conditions where multiple users try to redeem the same code simultaneously. The goal is an **atomic update**: a code's status changes from `available` to `redeemed` in a single, indivisible operation.

#### Core Mechanism: Database Transaction with Atomic Updates

The primary defense against double-spending is leveraging the atomicity and isolation properties of a relational database.

1.  **Atomic `UPDATE` Statement:**
    The most straightforward and efficient way is to use a conditional update statement.
    sql
    UPDATE coupon_codes
    SET status = 'redeemed', redeemed_by_user_id = ?, redeemed_at = NOW()
    WHERE code = ? AND status = 'available';
    
    The `WHERE` clause is key here. If the code is not `available`, or if the code doesn't exist, no rows will be updated. The database guarantees that this `UPDATE` operation is atomic. If two concurrent requests hit this, only one will succeed in updating the row; the other will find the `status` no longer `available`.

    The application then checks the number of rows affected by the `UPDATE`. If `1` row was affected, the redemption was successful. If `0` rows were affected, the code was either invalid, already redeemed, or expired.

2.  **Database Transaction with Pessimistic Locking (Less Ideal for High Concurrency):**
    For more complex scenarios where multiple steps depend on the coupon state *before* the final update, pessimistic locking can be used.
    sql
    START TRANSACTION;
    SELECT * FROM coupon_codes WHERE code = ? AND status = 'available' FOR UPDATE;
    -- If no row found, or status is not 'available', COMMIT and return error.
    -- Else, proceed with application logic (e.g., apply discount, create order).
    UPDATE coupon_codes
    SET status = 'redeemed', redeemed_by_user_id = ?, redeemed_at = NOW()
    WHERE code = ?;
    COMMIT;
    
    `FOR UPDATE` locks the selected row, preventing other transactions from modifying or locking it until the current transaction commits or rolls back. While it guarantees strong consistency, it can severely impact concurrency by introducing contention and potential deadlocks in high-traffic scenarios. The atomic `UPDATE` is generally preferred.

#### Enhancing Concurrency and Resilience:

*   **Idempotency Keys:**
    *   Clients (e.g., mobile apps) can send a unique `request_id` with each redemption attempt.
    *   The server stores this `request_id` alongside the redemption record. If the same `request_id` is received again (e.g., due to a network retry), the server returns the *original* result without re-processing. This prevents duplicate actions, though not necessarily preventing double-spending of the code itself (the atomic `UPDATE` handles that). It's more about preventing duplicate *request processing*.

*   **Distributed Caching (e.g., Redis):**
    *   While the database is the source of truth, a cache can improve read performance for checking code existence and initial status.
    *   **Caution:** Caching the `status` of a coupon is risky. If a code's status is cached as `available` but it gets redeemed in the database, the cache could serve stale data, leading to double-spend attempts.
    *   Best practice: Cache only `available` codes that haven't been touched, and aggressively invalidate cache entries or only read directly from the database for redemption attempts.
    *   A safer approach is to use Redis as a **distributed lock** for specific critical sections, but for simple single-record updates, the atomic DB `UPDATE` is usually sufficient and simpler.

*   **Asynchronous Processing:**
    *   After a successful atomic update in the database, the heavy lifting (e.g., applying discount to order, sending confirmation emails) can be offloaded to a **message queue** (e.g., Kafka, RabbitMQ).
    *   The initial redemption response can be fast, acknowledging the code is claimed, while background workers process subsequent steps. This improves user experience and system throughput.

### 2.3 System Components

*   **Coupon Service (Microservice):** Responsible for all coupon-related operations:
    *   `generateCodes(campaignId, count, ...)`
    *   `redeemCode(code, userId, orderId)`
    *   `validateCode(code, userId)`
    *   `expireCode(code)`
*   **Database (e.g., PostgreSQL, MySQL):** Primary data store for coupon codes, statuses, campaigns. Crucial for atomic updates and strong consistency.
*   **API Gateway:** Routes requests to the Coupon Service.
*   **Message Queue (e.g., Kafka):** For asynchronous post-redemption processing, analytics, notifications.
*   **Monitoring & Alerting:** To track redemption rates, errors, and system health.

## 3. Comparison / Trade-offs

Let's compare different approaches to preventing double-use, focusing on their suitability for high-concurrency environments.

| Feature               | Atomic SQL Update (`UPDATE ... WHERE status = 'available'`) | Database Pessimistic Locking (`SELECT ... FOR UPDATE`) | Distributed Lock (e.g., Redis Lock)                   | Idempotency Key (Client-side `request_id`)             |
| :-------------------- | :---------------------------------------------------------- | :----------------------------------------------------- | :---------------------------------------------------- | :----------------------------------------------------- |
| **Primary Goal**      | Guarantee single-use of code.                               | Guarantee single-use, prevent concurrent data modification. | Coordinate access to shared resources across services. | Prevent duplicate processing of client requests.         |
| **Pros**              | **Highly efficient**, leverages DB atomicity, high throughput. | Strong consistency, simple for complex multi-step transactions. | High performance, scales horizontally, external to DB. | Prevents retries from causing duplicate actions, client-agnostic. |
| **Cons**              | Only covers the `UPDATE` part, application logic must handle outcome. | **Low concurrency**, potential for deadlocks, higher latency. | Adds complexity, potential for lock expiration issues, requires careful implementation. | Relies on client, must be stored/checked; doesn't prevent other clients from using a code. |
| **Best For**          | **Core mechanism for redemption**, simple and robust.       | Complex, multi-step transactions with low-medium concurrency. | Coordinating tasks across multiple microservices.     | Preventing duplicate payments, handling network retries. |
| **Consistency Model** | Strong (via DB).                                            | Strong (via DB).                                       | Eventual (with care), or Strong (with careful implementation). | Eventual (if not combined with strong consistency).      |

> **Pro Tip:** For single-use coupon redemption, the **atomic SQL `UPDATE` statement** is almost always the preferred and most efficient core mechanism. Combine it with Idempotency Keys at the API level for better client experience and distributed messaging for asynchronous follow-ups. Avoid pessimistic locking for high-volume, single-record updates.

## 4. Real-World Use Case

Virtually every major consumer-facing platform leverages single-use coupon code systems:

*   **E-commerce Giants (Amazon, Shopify, Alibaba):** Used extensively for promotional campaigns, discounts, and customer loyalty programs. Imagine a Black Friday sale where millions of unique discount codes are released. The system must handle an immediate surge of redemption attempts without allowing double-spending.
*   **Food Delivery Services (Uber Eats, DoorDash, Deliveroo):** Offer unique codes for first-time users, specific restaurants, or special events. A single code error could lead to significant financial loss and customer dissatisfaction.
*   **Gaming Platforms (Steam, Epic Games Store):** Distribute unique codes for game keys, in-game items, or promotional discounts.
*   **Subscription Services (Netflix, Spotify):** Offer trial period codes or discount codes to attract new subscribers.

The "Why" is simple: These systems are critical for driving sales, acquiring new customers, retaining existing ones, and running effective marketing campaigns. The financial integrity and user trust of these platforms heavily rely on the robustness and correctness of their coupon redemption infrastructure. A flaw in this design could lead to massive financial losses due to fraudulent double redemptions or a poor user experience from failed legitimate redemptions.