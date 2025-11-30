---
title: "Design a 1-on-1 and group chat application. How would you handle message delivery, online presence, and read receipts? What protocol would you use (e.g., WebSockets)?"
date: 2025-11-30
categories: [System Design, Real-time Communication]
tags: [chat, websockets, systemdesign, realtime, messaging, architecture]
toc: true
layout: post
---

## 1. The Core Concept

Imagine a bustling digital post office, but instead of physical mail, it handles instantaneous digital messages. Not only does it deliver letters, but it also knows if your friend is currently at their mailbox, and even when they've opened your letter. That's essentially what we're building: a system for instant, reliable communication.

> **Definition:** A **chat application** is a real-time communication platform that enables users to send and receive messages instantly, either in private 1-on-1 conversations or within larger group contexts, often including features like presence indication and message status tracking.

## 2. Deep Dive & Architecture

Designing a robust chat application involves several interconnected services, each handling a specific aspect of the communication flow. The backbone of real-time communication in such a system is often a **persistent, bi-directional connection**.

### 2.1 Protocol Choice: WebSockets

For real-time chat, **WebSockets** are the undisputed champion. Unlike traditional HTTP requests (which are stateless and often short-lived), WebSockets provide a full-duplex communication channel over a single, long-lived TCP connection. This means both the client and server can send data to each other at any time, without constant polling.

**Why WebSockets?**

*   **Full-duplex:** Simultaneous two-way communication.
*   **Persistent connection:** Reduces overhead from repeated connection establishments.
*   **Low latency:** Messages are pushed instantly, not pulled.
*   **Efficient:** Lower overhead after the initial HTTP handshake compared to long-polling.

### 2.2 Core Architectural Components

A typical chat application architecture might look like this:


+---------------+      +-------------------+      +-----------------+      +---------------------+
| Client App    |----->| API Gateway/LB    |----->| Chat Service    |----->| Message Queue (Kafka) |
| (Web/Mobile)  |<-----+ (WebSocket Proxy) |<-----+ (Connection Mgr)|<-----+ (Pub/Sub)           |
+---------------+      +-------------------+      +-----------------+      +---------------------+
       |                                                    |                          |
       |  (Heartbeats)                                      |                          |
       |----------------------------------------------------+                          |
       |                                                    |                          |
       v                                                    v                          v
+---------------+                                  +-------------------+      +---------------------+
| Presence Svc  |                                  | DB (Metadata/Users)|<-----| Message Store Svc   |
| (Redis-backed)|                                  | (PostgreSQL/Mongo)|      | (Cassandra/MongoDB) |
+---------------+                                  +-------------------+      +---------------------+
       ^
       |
       | (Online Status Updates)
       |
       +---------------------------------------------------------------------------------------------+
                                                                                                     |
                                                                                                     |
                                                                                                     v
                                                                                           +---------------------+
                                                                                           | Notification Service|
                                                                                           | (APNS/FCM)          |
                                                                                           +---------------------+


*   **Client Application:** The front-end (web, iOS, Android) that users interact with. It establishes WebSocket connections and renders chat messages.
*   **API Gateway/Load Balancer:** Acts as an entry point, routing requests to appropriate services and handling WebSocket connection upgrades. Crucial for scaling.
*   **Chat Service:** The heart of the system. It manages active WebSocket connections, authenticates users, routes messages to recipients, and integrates with other services. This service needs to be horizontally scalable.
*   **Message Queue (e.g., Kafka, RabbitMQ):** Decouples services, handles message buffering, and ensures reliable message delivery. It's especially vital for fan-out scenarios in group chats.
*   **Message Store Service & Database:** Persists all chat messages. A NoSQL database (like Cassandra or MongoDB) is often preferred for its scalability, high write throughput, and flexible schema for evolving message types.
*   **Presence Service (e.g., Redis):** Tracks user online/offline status. Redis is ideal due to its in-memory nature for low-latency lookups and its Pub/Sub capabilities.
*   **Notification Service:** Sends push notifications (e.g., Firebase Cloud Messaging, Apple Push Notification Service) to users who are offline but have new messages.
*   **User/Metadata Database:** Stores user profiles, group configurations, conversation metadata, etc. A relational database (like PostgreSQL) might be suitable here for its strong consistency and complex querying capabilities.

### 2.3 Handling Message Delivery

Ensuring messages are delivered reliably and efficiently is paramount.

1.  **Sending a Message:**
    *   Client sends message `M` to **Chat Service** via WebSocket.
    *   **Chat Service** validates `M`, assigns a unique `message_id`, and publishes `M` to a **Message Queue**.
    *   **Chat Service** immediately acknowledges receipt to the sender client (`ACK`).

2.  **Storing the Message:**
    *   A **Message Store Service** consumes `M` from the **Message Queue** and persists it to the **Message Database**.
    *   This service is responsible for updating the `message_id` with `delivered` status once successfully stored.

3.  **Real-time Delivery to Recipients:**
    *   **Chat Service** also checks the **Presence Service** for the recipient's online status and active WebSocket connection.
    *   If online, the **Chat Service** pushes `M` directly to the recipient via their WebSocket connection.
    *   Recipient client acknowledges receipt of `M` to **Chat Service**.

4.  **Offline Delivery & Notifications:**
    *   If the recipient is offline, the **Chat Service** (or a dedicated handler consuming from the Message Queue) will trigger the **Notification Service** to send a push notification.
    *   When the recipient comes online, their client fetches any missed messages from the **Message Database** (using `last_read_message_id` or similar).

> **Pro Tip: At-Least-Once Delivery**
> To ensure messages are never lost, implement **at-least-once delivery**. This involves clients generating a unique `client_message_id`, server-side deduplication, and acknowledgments (ACKs) at each stage of the delivery pipeline. If an ACK isn't received, the sender (client or service) should retry.

### 2.4 Handling Online Presence

Presence information (online, offline, away) is critical for a responsive chat experience.

1.  **Client Heartbeats:**
    *   Clients periodically send `ping` messages (heartbeats) over their WebSocket connection to the **Chat Service** (e.g., every 30-60 seconds).
    *   If the **Chat Service** doesn't receive a `ping` for a configured duration (e.g., 90 seconds), it considers the client disconnected.

2.  **Presence Service (Redis):**
    *   Upon connection/heartbeat, the **Chat Service** updates the user's status in the **Presence Service** (e.g., `SET user:<user_id>:status online EX 90`). Redis's `EX` (expire) command automatically handles status changes if heartbeats stop.
    *   When a user explicitly disconnects, the **Chat Service** updates their status to `offline`.

3.  **Publishing Status Changes:**
    *   Any change in a user's presence status triggers the **Chat Service** to publish an update to a Redis Pub/Sub channel.
    *   Other connected **Chat Services** (in a distributed system) and clients subscribed to presence updates for their contacts will receive these notifications and update their UI accordingly.

### 2.5 Handling Read Receipts

Read receipts inform the sender when their message has been seen by the recipient. This involves a three-state model:

1.  **Sent:** Message successfully received by the server and persisted (server-side ACK).
2.  **Delivered:** Message successfully pushed to the recipient's device (client-side ACK to server).
3.  **Read:** Recipient has viewed the message in the chat interface.

**Process:**

*   **Message State Tracking:** Each message stored in the **Message Database** has a `status` field (e.g., `SENT`, `DELIVERED`, `READ`).
*   **Delivery Acknowledgment:** When a message is successfully pushed to a recipient's client via WebSocket, the client sends a `DELIVERED` acknowledgment back to the **Chat Service**. The service updates the message status in the DB.
*   **Read Acknowledgment:** When the recipient's client displays the message (e.g., scrolls into view, chat window opened), it sends a `READ` acknowledgment to the **Chat Service**.
*   **Notify Sender:** The **Chat Service** updates the message status in the DB to `READ`. It then sends a `message_status_update` notification to the original sender's active WebSocket connection, updating their UI.
*   **Group Chats:** For group chats, `read` receipts often track which specific members have read the message, potentially storing a list of `user_ids` associated with the `read` status for a given message.

## 3. Comparison / Trade-offs

Choosing the right communication protocol is a fundamental decision impacting performance, complexity, and resource usage. Let's compare WebSockets with two common alternatives for "real-time" communication.

| Feature               | WebSockets                                     | Long Polling                                       | Server-Sent Events (SSE)                        |
| :-------------------- | :--------------------------------------------- | :------------------------------------------------- | :---------------------------------------------- |
| **Bidirectional?**    | **Yes (Full-duplex)**                          | No (Client-server via separate requests)           | No (Server-to-client only)                      |
| **Connection Type**   | Persistent, single TCP connection              | Many short-lived HTTP connections (or one long-held)| Persistent, single HTTP connection              |
| **Latency**           | **Very low (Push-based)**                      | Moderate (Depends on polling interval/timeout)     | Low (Push-based)                                |
| **Overhead**          | Low after handshake                            | High (repeated HTTP headers)                       | Low (after handshake, lightweight HTTP headers) |
| **Complexity**        | Moderate (Stateful server-side management)     | Low (Stateless, standard HTTP)                     | Low (Stateless, standard HTTP)                  |
| **Use Case**          | **Chat, gaming, collaborative editing**        | Older chat, infrequent updates                     | News feeds, stock tickers, real-time dashboards |
| **Key Advantage**     | Most efficient for true real-time, bi-dir data | Simpler to implement in legacy systems             | Efficient for server-to-client streaming data   |
| **Key Disadvantage**  | Stateful server logic can be complex to scale  | High resource consumption, higher latency          | Unidirectional (no client -> server push)       |

For a feature-rich, interactive chat application requiring constant two-way communication, **WebSockets** offer the best performance and user experience, despite the added server-side complexity of managing stateful connections.

## 4. Real-World Use Case

The design principles discussed here are the foundation of virtually every modern chat application you use daily.

**WhatsApp, Slack, Discord, Facebook Messenger, Microsoft Teams** – these platforms all leverage architectures similar to what we've outlined.

**Why is this architecture preferred?**

*   **Instantaneity:** Users expect messages to appear instantly. WebSockets and efficient message queues make this possible.
*   **Reliability:** Messages must not be lost. At-least-once delivery, persistent storage, and retries ensure this.
*   **Scalability:** These applications serve billions of users and millions of concurrent connections. A distributed microservices architecture, combined with highly scalable databases and message queues, is essential to handle such loads.
*   **Responsiveness:** Real-time presence and read receipts enhance the user experience by providing immediate feedback on communication status.
*   **Global Reach:** Services like push notifications are critical for engaging users across different devices and time zones, even when they are not actively using the app.

By adopting these patterns, developers can build robust, scalable, and delightful communication experiences that form the backbone of modern digital interaction.