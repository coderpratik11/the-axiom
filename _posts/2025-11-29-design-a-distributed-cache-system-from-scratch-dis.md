---
title: "Design a distributed cache system from scratch. Discuss the challenges of cache invalidation, eviction policies (LRU, LFU), and preventing the 'thundering herd' problem."
date: 2025-11-29
categories: [System Design, Caching]
tags: [distributed cache, system design, cache invalidation, eviction policies, thundering herd, architecture, performance]
toc: true
layout: post
---

## 1. The Core Concept

Imagine you're managing a bustling library. The main archive holds millions of books, but certain popular titles are requested dozens of times a day. If every request means a trip to the deep, slow archive, patrons will wait endlessly. A smart librarian would keep copies of these popular books right at the front desk, ready for immediate checkout.

This "front desk" is analogous to a **cache** in a software system. A cache is a high-speed data storage layer that stores a subset of data, typically transient, so that future requests for that data can be served up faster than retrieving it from the primary data store (like a database or an external API).

> **Definition:** A **distributed cache system** is a collection of networked servers that pool their memory resources to store data accessible to multiple applications or services. Its primary goal is to improve application performance, reduce the load on backend data sources, and enhance scalability by serving frequently requested data quickly and efficiently.

## 2. Deep Dive & Architecture

Designing a distributed cache involves several critical components and tackling inherent challenges.

### Architectural Components

A typical distributed cache system comprises:

*   **Cache Client:** Integrated into your application, responsible for interacting with the cache servers. It uses a **hashing algorithm** (often **consistent hashing**) to determine which cache server node holds or should hold a piece of data.
*   **Cache Server Nodes:** A cluster of independent servers, each storing a portion of the cached data. These nodes are stateless regarding the application, meaning any node can serve any client request if it contains the data.
*   **Data Store (Origin):** The primary source of truth (e.g., a relational database, NoSQL database, or external service) that the cache eventually pulls data from if it's not present or is stale.

#### Data Distribution: Consistent Hashing

To effectively distribute data across multiple cache nodes and minimize data movement during scaling events (adding or removing nodes), **consistent hashing** is crucial.


function consistent_hash(key, nodes):
    # Map both keys and nodes to a hash ring
    hash_value = hash(key)
    # Find the first node on the ring >= hash_value
    # If no such node, wrap around to the first node
    return find_node_on_ring(hash_value, nodes)


Consistent hashing ensures that when a node is added or removed, only a small fraction of the keys need to be remapped and moved, rather than a complete redistribution.

### Challenges and Solutions

#### 2.1. Cache Invalidation

This is often cited as one of the hardest problems in computer science: ensuring the cached data remains consistent with the source of truth.

*   **Time-To-Live (TTL):** The simplest approach. Each cache entry is assigned a lifespan after which it's automatically evicted.
    *   **Pros:** Easy to implement, guarantees eventual consistency.
    *   **Cons:** Data can be stale until TTL expires.
*   **Write-Through:** Data is written to the cache **and** the primary data store simultaneously.
    *   **Pros:** Data in cache is always up-to-date with the database.
    *   **Cons:** Higher write latency, as both operations must succeed.
*   **Write-Back:** Data is written only to the cache first, and then asynchronously written to the primary data store.
    *   **Pros:** Low write latency.
    *   **Cons:** Potential for data loss if the cache node crashes before data is persisted.
*   **Cache-Aside:** The application directly manages reading and writing to the cache.
    *   **Read:** Application checks cache first. If found (cache hit), return data. If not (cache miss), fetch from DB, store in cache, then return.
    *   **Write:** Application writes to DB, then explicitly invalidates or updates the corresponding entry in the cache.
    *   **Pros:** Most common and flexible, cache and DB are loosely coupled.
    *   **Cons:** Application code complexity increases, potential for race conditions if not handled carefully.
*   **Publish/Subscribe (Pub/Sub) for Active Invalidation:** When the primary data store is updated, it publishes an event (e.g., via Kafka or a message queue). Cache nodes subscribe to these events and invalidate or update their copies of the affected data.
    *   **Pros:** Near real-time consistency, reactive.
    *   **Cons:** Adds complexity with message queues.

> **Pro Tip:** For most web applications, a combination of **Cache-Aside** with **TTL** is a good starting point. For critical data requiring strong consistency, consider active invalidation via Pub/Sub or **Write-Through** for specific operations.

#### 2.2. Eviction Policies

When the cache reaches its capacity limit, a policy is needed to decide which data to remove to make space for new entries.

*   **Least Recently Used (LRU):** Evicts the item that has not been accessed for the longest period.
    *   **Implementation:** Typically uses a combination of a **doubly linked list** (to maintain access order) and a **hash map** (for O(1) lookups).
    *   **Use Case:** Good for data with high temporal locality (data recently accessed is likely to be accessed again soon).
*   **Least Frequently Used (LFU):** Evicts the item that has been accessed the fewest times.
    *   **Implementation:** More complex, often involves a **frequency map** (e.g., `map<key, frequency>`) and a **doubly linked list of doubly linked lists** (where each inner list holds items with the same frequency), or a min-heap.
    *   **Use Case:** Good for data with high frequency locality (data frequently accessed is likely to be accessed again).
*   **Other Policies:**
    *   **First-In, First-Out (FIFO):** Evicts the oldest item regardless of usage. Simple but often inefficient.
    *   **Random Replacement (RR):** Evicts a random item. Simple but unpredictable.


# Conceptual LRU implementation (simplified)
class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = {} # key -> node
        self.head = Node(None, None) # dummy head
        self.tail = Node(None, None) # dummy tail
        self.head.next = self.tail
        self.tail.prev = self.head

    def get(self, key):
        if key in self.cache:
            node = self.cache[key]
            self._move_to_front(node)
            return node.value
        return -1

    def put(self, key, value):
        if key in self.cache:
            node = self.cache[key]
            node.value = value
            self._move_to_front(node)
        else:
            node = Node(key, value)
            self.cache[key] = node
            self._add_to_front(node)
            if len(self.cache) > self.capacity:
                self._remove_from_end()


#### 2.3. Preventing the 'Thundering Herd' Problem

The "Thundering Herd" problem occurs when a cache item expires or is invalidated, and suddenly, a large number of concurrent requests for that same item all miss the cache and simultaneously hit the backend data store. This can overload the database, causing performance degradation or even crashes.

*   **Request Coalescing/Deduplication:** When an item is not in the cache, the first request acquires a lock for that specific key. Subsequent requests for the same key wait on this lock. Once the first request fetches the data from the origin and populates the cache, it releases the lock, and all waiting requests can then retrieve the data from the now-populated cache.
    *   **Mechanism:** Uses distributed locks (e.g., Redis `SETNX`, ZooKeeper, etcd) or in-memory locks within a single cache node.
    
    function get_with_deduplication(key):
        data = cache.get(key)
        if data is not None:
            return data
        
        # Acquire a distributed lock for this key
        if acquire_lock(key):
            try:
                data = cache.get(key) # Check again, might have been populated while waiting for lock
                if data is not None:
                    return data
                
                data = fetch_from_database(key)
                cache.set(key, data)
                return data
            finally:
                release_lock(key)
        else:
            # Wait for a short period and retry or fetch from cache again
            # Or block until lock is released (blocking approach)
            wait_on_lock_release(key) 
            return cache.get(key)
    
*   **Jitter/Randomized Expiration:** Instead of setting a fixed TTL for all instances of a cache item, add a small random "jitter" to the expiration time. This staggers the expiration events, preventing a large batch of items from expiring at the exact same moment.
*   **Cache Stampede Protection (Probabilistic Early Recomputation):** Instead of waiting for an item to expire, an item can be "soft-expired" or given a "grace period". When an item is close to expiry, if a request comes in, a single process might proactively recompute/refetch the item in the background while still serving the old (slightly stale) data. Only if the item is truly expired or the recomputation fails would it hit the "thundering herd" scenario.

## 3. Comparison / Trade-offs

Let's compare the two primary eviction policies: LRU and LFU.

| Feature               | Least Recently Used (LRU)                                    | Least Frequently Used (LFU)                                  |
| :-------------------- | :----------------------------------------------------------- | :----------------------------------------------------------- |
| **Logic**             | Evicts the item that has not been accessed for the longest time. | Evicts the item that has been accessed the fewest times.     |
| **Complexity**        | Relatively simpler to implement (doubly linked list + hash map). | More complex to implement (frequency map + min-heap or list of lists). |
| **Memory Usage**      | Moderate overhead for linked list pointers.                  | Higher overhead due to storing access counts and more complex data structures. |
| **Performance (Hit Rate)** | Excellent for data exhibiting temporal locality (e.g., session data, recently viewed products). | Excellent for data exhibiting frequency locality (e.g., highly popular static content, top trending items). |
| **Cold Start**        | Adapts quickly to new access patterns. A new popular item will quickly move to the front. | Slower to adapt. A newly popular item might be evicted quickly if its frequency count is low, even if it's currently popular. |
| **Recency vs. Frequency** | Favors recency.                                              | Favors frequency.                                            |
| **Use Cases**         | Web page caching, API response caching, recently used files.  | CDN caching of popular content, DNS query caching, frequently accessed database rows. |
| **Drawbacks**         | A single burst of access to an old item can save it from eviction, pushing out genuinely more useful recent items. | Items that were very popular historically but are no longer frequently accessed can persist in the cache for a long time. |

> **Warning:** Choosing an eviction policy is crucial and context-dependent. LRU is generally a good default, but LFU can be superior for content that has consistent, long-term popularity. Consider your data access patterns carefully.

## 4. Real-World Use Case

Distributed caching is a cornerstone of modern, high-scale internet services.

**Netflix** is an excellent example. When you browse for a movie, the movie metadata, user profiles, personalized recommendations, and even portions of the content delivery logic are all heavily cached across various layers.

*   **Why Netflix uses distributed caching:**
    *   **Reduced Database Load:** Without caching, every request for a movie title, user preference, or recommendation would hit their backend databases, potentially overwhelming them. Caching absorbs the vast majority of read requests.
    *   **Lower Latency:** Data stored closer to the user or application tier (in a cache) can be retrieved in milliseconds or microseconds, drastically improving the responsiveness of the user interface. Imagine if every click took seconds to load because it had to query a distant database.
    *   **Increased Scalability:** By offloading reads from databases, Netflix can scale its application servers and cache clusters independently, allowing them to handle millions of concurrent users efficiently.
    *   **Cost Efficiency:** Reducing database read load can translate into significant cost savings, as highly provisioned databases are expensive.
    *   **Improved Resiliency:** Caches can act as a buffer. If a backend database experiences a temporary slowdown or outage, the cache might still be able to serve slightly stale data, providing a degraded but functional experience rather than a complete service disruption.

Netflix's use of caching spans from **CDN (Content Delivery Network)** providers caching video segments closer to you, to their internal services caching recommendations and user data in systems like **EVCache** (an in-memory distributed cache built on top of Memcached). This multi-layered caching strategy ensures a seamless, fast, and reliable streaming experience for users worldwide.