---
title: "Design the backend for a news feed. Discuss the fan-out approach (push vs. pull) and how you would handle the 'celebrity' problem."
date: 2025-11-29
categories: [System Design, News Feed]
tags: [newsfeed, systemdesign, fanout, pushpull, scalability, celebrityproblem, architecture, distributedsystems, microservices]
toc: true
layout: post
---

Building a scalable and reliable news feed is a quintessential system design challenge. It touches on data modeling, distributed systems, caching, and various trade-offs that Principal Software Engineers face daily. In this post, we'll dissect the core concepts, explore different fan-out strategies, and tackle the notorious "celebrity problem."

## 1. The Core Concept

Imagine your social media feed. It's a dynamic, personalized stream of content from people you follow, curated just for you. Designing the backend for such a system involves ensuring that content posted by one user efficiently reaches all their followers, often in real-time.

Think of a news feed like a personalized newspaper delivery service. When someone publishes a story, we need to decide how to get that story into the "mailboxes" of everyone who subscribed to their updates. Do we immediately print copies and deliver them, or do we wait for each subscriber to ask for their latest paper? This choice defines our **fan-out strategy**.

> A **News Feed Backend** is a system designed to aggregate content from various sources (users, pages, groups) that a user follows, process it, and present it as a personalized, chronological, or algorithmically ranked stream of updates to the requesting user. The primary challenge lies in efficiently distributing content to a potentially massive number of followers.

## 2. Deep Dive & Architecture

At a high level, a news feed system typically involves services for user management, content creation, follow relationships, and the actual feed generation and serving. Our focus here will be on the latter two: how content "fans out" to followers.

### Core News Feed Components:

1.  **Post Service:** Handles creating, storing, and retrieving content (text, images, videos).
2.  **Follow Service:** Manages `user_id -> followed_user_id` relationships. Essential for determining who should receive which content.
3.  **Feed Service:** The orchestrator that generates and serves the personalized feed for each user. This is where fan-out strategies come into play.

### Fan-out Approaches

The choice of fan-out strategy significantly impacts system performance, scalability, and complexity.

#### 2.1. Fan-out on Write (Push Model)

In this model, when a user posts new content, that content is immediately pushed to the "inbox" or "timeline" of all their followers.

**Architectural Flow:**
1.  User `A` posts content `C`.
2.  `Post Service` stores `C`.
3.  `Follow Service` identifies all followers of `A` (e.g., `F1, F2, ..., Fn`).
4.  `Fan-out Service` pushes `C` to the individual feeds (inboxes) of `F1, F2, ..., Fn`. This might involve writing to a `UserFeed` table in a low-latency database (e.g., Cassandra, Redis).
5.  When `F1` requests their feed, `Feed Service` simply reads `F1`'s pre-populated inbox.

mermaid
graph TD
    UserA[User A] -- Posts Content C --> PostService
    PostService --> ContentStorage[Content Storage]
    PostService --> FanoutService[Fan-out Service]
    FanoutService -- Gets Followers from --> FollowService[Follow Service]
    FanoutService -- Pushes Content C to N Inboxes --> UserFeedDB[User Feed Database]
    UserF1[User F1] -- Requests Feed --> FeedService[Feed Service]
    FeedService -- Reads F1's Inbox --> UserFeedDB
    UserFeedDB -- Returns F1's Feed --> UserF1


#### 2.2. Fan-out on Read (Pull Model)

In contrast, the pull model stores content in an "outbox" associated with the posting user. Followers fetch their feed by querying the outboxes of all the users they follow and then merging the results.

**Architectural Flow:**
1.  User `A` posts content `C`.
2.  `Post Service` stores `C` in `A`'s personal outbox (e.g., `UserOutbox` table).
3.  When `F1` requests their feed:
    a.  `Feed Service` queries `Follow Service` to get all users `F1` follows (e.g., `A, B, D`).
    b.  `Feed Service` retrieves recent content from the outboxes of `A, B, D`.
    c.  `Feed Service` merges and sorts this content to create `F1`'s feed.
    d.  This aggregated feed is then served to `F1`.

mermaid
graph TD
    UserA[User A] -- Posts Content C --> PostService
    PostService --> UserOutbox[User Outbox Database]
    UserF1[User F1] -- Requests Feed --> FeedService[Feed Service]
    FeedService -- Gets Followed Users from --> FollowService[Follow Service]
    FeedService -- Pulls Content from Multiple --> UserOutbox
    FeedService -- Aggregates & Sorts --> F1Feed[F1's Aggregated Feed]
    F1Feed --> UserF1


#### 2.3. Hybrid Model

Most real-world systems use a **hybrid approach**, combining the best of both worlds. For users with a moderate number of followers, fan-out on write is efficient. For users with millions of followers (the "celebrities"), fan-out on read becomes more practical, often augmented with heavy caching.

### 2.4. The 'Celebrity Problem'

The "celebrity problem" (also known as the "hot spot" or "super-fan-out" problem) arises when a user has an extremely large number of followers (e.g., millions). This user is a "celebrity" in the context of the platform.

**Impact:**
-   **Fan-out on Write:** When a celebrity posts, pushing content to millions of followers' inboxes can overwhelm the `Fan-out Service` and the underlying database. This leads to high write latency, increased resource consumption, and potential system instability. Imagine a write amplification factor of 1:10,000,000 for every post!
-   **Fan-out on Read:** While it avoids the write storm, followers of a celebrity would experience slower feed generation as their feed service has to fetch and merge content from potentially thousands of followed users, including a celebrity's outbox which itself might be frequently updated.

**How to Handle the Celebrity Problem:**

1.  **Dedicated Celebrity Outboxes (Pull for Celebrities):**
    -   Treat celebrities differently. Their posts are only written to their own outbox.
    -   Followers of celebrities then **pull** content from these outboxes when they request their feed.
    -   This effectively shifts the burden from the write path to the read path for celebrity content.

2.  **Aggressive Caching:**
    -   For celebrity content (which is highly accessed), cache it heavily at multiple layers (CDN, edge caches, in-memory caches).
    -   When a follower's `Feed Service` needs celebrity content, it first checks the cache. This reduces direct database reads.

3.  **Tiered Fan-out:**
    -   Prioritize fan-out. For the *most engaged* followers of a celebrity, you might still push content. For others, use a pull model with caching.
    -   This is complex but can optimize the user experience for the most valuable interactions.

4.  **Materialized Views / Pre-computation:**
    -   For very popular celebrities, you might pre-compute a "public timeline" or a "celebrity feed" that is frequently refreshed and served from a fast data store. This acts like a giant cached outbox.

5.  **Asynchronous Processing with Message Queues:**
    -   Regardless of the fan-out strategy, use message queues (e.g., Kafka, RabbitMQ) to decouple the posting action from the fan-out process. This absorbs spikes and allows the system to process fan-out asynchronously and reliably, even if it's eventually pulling from celebrity outboxes.

python
# Conceptual representation of a hybrid fan-out logic
def distribute_post(post_id, author_id):
    followers = FollowService.get_followers(author_id)
    
    if len(followers) > CELEBRITY_THRESHOLD:
        # Handle as a celebrity post: lazy fan-out (pull)
        # Store post in author's outbox and update a "celebrity_post" index
        PostService.store_in_outbox(post_id, author_id)
        # Invalidate cache for this celebrity's feed
        CacheService.invalidate_celebrity_feed(author_id)
        print(f"Post {post_id} from celebrity {author_id} stored in outbox and cache invalidated.")
    else:
        # Handle as a regular post: eager fan-out (push)
        messages = []
        for follower_id in followers:
            messages.append({
                'post_id': post_id,
                'author_id': author_id,
                'follower_id': follower_id
            })
        
        # Publish messages to a fan-out queue for asynchronous processing
        MessageQueue.publish_batch(FANOUT_QUEUE, messages)
        print(f"Post {post_id} from {author_id} pushed to {len(followers)} followers via queue.")

# In the Feed Service when a user requests their feed:
def get_user_feed(user_id):
    followed_users = FollowService.get_followed_users(user_id)
    
    feed_items = []
    celebrity_posts_to_fetch = []
    
    for followed_user_id in followed_users:
        if FollowService.is_celebrity(followed_user_id):
            # Pull from celebrity's outbox (or cached celebrity feed)
            celebrity_posts_to_fetch.append(followed_user_id)
        else:
            # Read from pre-populated inbox for non-celebrities
            inbox_items = UserFeedDB.get_inbox_for_user(user_id, followed_user_id)
            feed_items.extend(inbox_items)
            
    # Fetch celebrity posts (can be cached or directly from outbox)
    for celebrity_id in celebrity_posts_to_fetch:
        cached_posts = CacheService.get_celebrity_feed(celebrity_id)
        if cached_posts:
            feed_items.extend(cached_posts)
        else:
            # Fallback to database if not in cache
            db_posts = PostService.get_outbox_posts(celebrity_id)
            feed_items.extend(db_posts)
            CacheService.set_celebrity_feed(celebrity_id, db_posts) # Cache for next time

    return sorted(feed_items, key=lambda x: x['timestamp'], reverse=True)



## 3. Comparison / Trade-offs

Here's a comparison of Fan-out on Write (Push) vs. Fan-out on Read (Pull):

| Feature               | Fan-out on Write (Push Model)                                 | Fan-out on Read (Pull Model)                                   |
| :-------------------- | :------------------------------------------------------------ | :------------------------------------------------------------- |
| **Read Performance**  | **Excellent (O(1))**: Feeds are pre-computed, simple read from inbox. | **Variable (O(N*M))**: N = followed users, M = posts per user. Requires aggregation and sorting. Can be slow. |
| **Write Performance** | **Poor for Celebrities**: High write amplification; costly as follower count grows. | **Excellent (O(1))**: Simple write to author's outbox, regardless of followers. |
| **Storage**           | High duplication: Each post stored in `N` inboxes.            | Low duplication: Each post stored once in author's outbox.     |
| **Complexity**        | Write path is complex (distributing to many followers). Read path is simple. | Write path is simple. Read path is complex (aggregation, merging, sorting). |
| **Real-time Updates** | Easier to achieve true real-time updates as content is pushed directly. | Updates depend on read frequency; less inherently real-time without active polling or notification. |
| **Celebrity Problem** | **Major Issue**: Prone to bottlenecks and system overload due to massive write load. | Better suited, as write load doesn't depend on follower count. Read load becomes the challenge. |
| **Use Case Fit**      | Platforms where real-time feed updates are critical, and most users have moderate followers (e.g., initial Twitter, microblogging). | Platforms with many irregular posters or where read latency can be tolerated (e.g., news sites, less active social networks, initial Facebook). |

## 4. Real-World Use Case

Almost every major social platform implements a news feed backend, and they invariably land on a **hybrid fan-out model** to balance the trade-offs, particularly for managing the celebrity problem.

**Twitter (now X):** Twitter famously started with a pure fan-out on write model. As it scaled, particularly with celebrity accounts, this became unsustainable. They evolved to a sophisticated hybrid system:
-   **Fan-out on Write** is still used for the vast majority of users who have a moderate number of followers. When you post, your tweet is pushed to the timelines of your followers into a distributed "timeline service" (e.g., built on technologies like Manhattan, their custom key-value store).
-   **Fan-out on Read (with heavy caching)** is employed for celebrities and users with extremely large follower counts. When a celebrity tweets, it's written to their outbox. Followers of this celebrity then have their feeds generated by pulling content from these celebrity outboxes, along with the pushed content from their other followed users. This celebrity content is heavily cached to ensure fast reads.

**Why this approach?**
Twitter needs to deliver content quickly to millions of users. The hybrid model allows them to optimize for both fast writes (for the many regular users) and fast reads (by pre-computing feeds where possible), while gracefully handling the extreme scale challenges posed by celebrities. They leverage distributed databases (like Redis for in-memory caching of timelines, and their custom database solutions), message queues (Kafka for event processing), and extensive caching layers (CDNs, edge caches) to achieve this at scale.

Designing a news feed backend is an exercise in understanding workload patterns, anticipating bottlenecks, and making pragmatic trade-offs to achieve desired performance and scalability goals. The fan-out strategies and the specific handling of the celebrity problem are central to this design.