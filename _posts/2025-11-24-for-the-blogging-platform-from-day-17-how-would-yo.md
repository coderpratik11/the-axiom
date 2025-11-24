---
title: "Solving Over-fetching and Under-fetching in a Blogging Platform with GraphQL"
date: 2025-11-24
categories: [System Design, API Design]
tags: [graphql, rest, api, overfetching, underfetching, bloggingplatform, architecture, frontend]
toc: true
layout: post
---

As a Principal Software Engineer, I often encounter discussions around API design, particularly concerning efficiency and flexibility. One of the most common pain points with traditional REST APIs, especially as applications grow in complexity, is the problem of **over-fetching** and **under-fetching** data. For our blogging platform from Day 17, let's explore how **GraphQL** provides an elegant solution to these challenges.

---

## 1. The Core Concept

Imagine you're at a custom burger joint. With a traditional REST API, it's like ordering a pre-defined "Classic Burger" meal. Sometimes, you might not want the pickles (that's **over-fetching** – you get more than you need). Other times, you want an extra side of chili cheese fries that aren't included with the "Classic Burger" and you have to make a separate order (that's **under-fetching** – you don't get everything you need in one go, requiring multiple requests).

Now, picture a system where you can explicitly tell the kitchen exactly what you want: "A burger, no pickles, extra cheese, and a side of chili cheese fries." That's the essence of GraphQL.

> **GraphQL** is an open-source data query and manipulation language for APIs, and a runtime for fulfilling queries with existing data. It empowers clients to specify precisely what data they need, thereby effectively resolving the over-fetching and under-fetching problems inherent in many traditional REST API approaches.

## 2. Deep Dive & Architecture

In the context of our blogging platform:

### The RESTful Dilemma

1.  **Over-fetching:**
    If we have a REST endpoint like `GET /api/posts`, it might return a list of posts, each with `id`, `title`, `content`, `authorId`, `createdAt`, `updatedAt`, `tags`, etc.
    However, if our client only needs to display a list of post titles for a navigation menu, it's receiving a lot of unnecessary `content`, `updatedAt` timestamps, and full `tags` arrays. This wastes bandwidth and client-side processing power.

2.  **Under-fetching:**
    Consider showing a single post page. Our client might first call `GET /api/posts/{postId}` to get the post details. This response includes `authorId`. To display the author's name and avatar, the client then needs to make a *second* request to `GET /api/users/{authorId}`. If we also want to display comments, that's a *third* request to `GET /api/posts/{postId}/comments`. This cascade of requests (N+1 problem) severely impacts performance, especially on mobile networks.

### GraphQL to the Rescue

GraphQL addresses these issues by shifting the control of data fetching to the client.

*   **Single Endpoint:** Unlike REST with its many resource-specific endpoints, a GraphQL API typically exposes a **single endpoint** (e.g., `/graphql`). All data requests, regardless of type, go through this single entry point.
*   **Client-driven Queries:** Clients send a **query** (a string defining the data shape) to the GraphQL server. The server then responds with *only* the data requested, matching the exact structure of the query.
*   **Strongly Typed Schema:** At the heart of a GraphQL API is its **schema**. This schema defines all the types of data that can be queried (e.g., `Post`, `User`, `Comment`), their fields, and the relationships between them. This strong typing provides clarity, enables powerful tooling, and acts as a contract between client and server.
*   **Resolvers:** On the server-side, **resolvers** are functions responsible for fetching the data for a specific field in the schema. When a query comes in, the GraphQL engine traverses the query, calling the appropriate resolvers to build the final response.

Let's illustrate with examples for our blogging platform:

#### Avoiding Over-fetching (List of Post Titles)

graphql
query GetPostTitles {
  posts {
    id
    title
    # No 'content', 'author', 'tags', etc., if not needed
  }
}

The server will only return `id` and `title` for each post, exactly what's requested.

#### Avoiding Under-fetching (Single Post with Author and Tags)

graphql
query GetFullPostDetails($postId: ID!) {
  post(id: $postId) {
    id
    title
    content
    createdAt
    author { # Nested fields for related data
      id
      name
      email
    }
    tags {
      id
      name
    }
    comments { # Even comments can be fetched in the same query
      id
      content
      createdAt
      author {
        name
      }
    }
  }
}

Here, a single query fetches the post, its author's details, its associated tags, *and* its comments (including comment authors), all in **one network request**. This drastically reduces round-trips and improves performance.

> **Pro Tip:** While GraphQL inherently solves over-fetching and under-fetching at the API layer, careful design of your **schema** and efficient **resolver** implementations (especially addressing the N+1 problem with techniques like **data loaders**) are crucial for optimal performance on the server-side.

## 3. Comparison / Trade-offs

Let's compare the traditional REST approach with GraphQL for our blogging platform, focusing on the problems they solve and their trade-offs.

| Feature / Aspect             | Traditional REST API                                                                                                           | GraphQL API                                                                                                                                                                  |
| :--------------------------- | :----------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Data Fetching Paradigm**   | Server-driven; fixed resource structures per endpoint. Client gets what the endpoint provides.                                 | Client-driven; clients explicitly specify the required data shape.                                                                                                           |
| **Over-fetching Mitigation** | Often requires creating multiple specialized endpoints (e.g., `/posts/summary`) or custom query parameters (`?fields=id,title`). | Inherently designed to avoid over-fetching as clients request *only* the necessary fields, minimizing payload size.                                                       |
| **Under-fetching Mitigation**| Leads to multiple round-trips (N+1 problem) to different endpoints (e.g., `GET /posts/{id}` then `GET /authors/{id}`).         | Solved by allowing nested queries to fetch related data (e.g., post, author, comments) in a **single network request**.                                                    |
| **Number of Endpoints**      | Multiple, resource-centric endpoints (e.g., `/posts`, `/users`, `/comments`).                                                  | Typically a single endpoint (e.g., `/graphql`) for all data operations.                                                                                                      |
| **Network Efficiency**       | Can be less efficient due to multiple requests or larger payloads containing unnecessary data.                                 | More efficient as it minimizes network round-trips and transfers only the requested data, which is crucial for mobile clients.                                             |
| **Complexity (Server-Side)** | Simpler for basic CRUD operations. Can become complex when custom filtering, sorting, or projection logic is needed across many endpoints. | Higher initial setup complexity for defining a robust **schema**, writing **resolvers**, and implementing performance optimizations (e.g., DataLoaders for N+1).                 |
| **Complexity (Client-Side)** | Simple HTTP requests (e.g., `fetch` or `axios`), but managing data from multiple endpoints and stitching it together can be complex. | Query construction requires understanding the schema. However, powerful client-side libraries (e.g., Apollo Client, Relay) simplify state management, caching, and data aggregation. |
| **Versioning**               | Common to version APIs (e.g., `/v1/posts`, `/v2/posts`), which can lead to maintenance overhead and redundancy.               | Schema evolution allows adding new fields without breaking existing clients. Deprecation can be handled gracefully within the schema without requiring new endpoints.          |

## 4. Real-World Use Case

GraphQL isn't just a theoretical concept; it's a proven solution used by some of the largest and most data-intensive applications in the world.

1.  **Facebook (the creator):** The original motivation behind GraphQL was to power Facebook's mobile applications, which needed to fetch complex, dynamic data for various UI components with minimal network overhead. It allowed them to build a highly adaptable and performant client-server architecture.
2.  **Netflix:** Uses GraphQL in their **Backend-for-Frontend (BFF)** architecture. Netflix serves diverse clients (smart TVs, web browsers, mobile phones) with varying data requirements. GraphQL enables them to aggregate data from numerous microservices into a single, optimized payload tailored precisely for each client's specific UI, significantly reducing over-fetching and under-fetching across a highly distributed system.
3.  **Shopify:** Their Admin API, used by developers to build custom e-commerce apps, is built on GraphQL. This empowers developers to integrate with Shopify's platform by querying only the exact data they need, avoiding the overhead of fetching vast amounts of irrelevant data that a traditional REST API might return. This flexibility accelerates third-party developer productivity.
4.  **GitHub:** Provides a public GraphQL API for interacting with its platform. This allows developers to build highly customized tools and integrations, fetching specific repository, user, or issue data in a single request, rather than making multiple calls to different REST endpoints.

**Why it's suitable in these scenarios (and for our blogging platform):**

*   **Complex and Evolving UIs:** Applications with highly dynamic interfaces and diverse data needs benefit greatly from the client's ability to define its data requirements. This is perfect for a blogging platform with various views (homepage, post detail, author profile, tag archives) each needing different subsets of data.
*   **Mobile-First Development:** Network efficiency is paramount for mobile applications. By minimizing payload sizes and reducing the number of round-trips, GraphQL significantly improves performance and responsiveness on constrained mobile networks.
*   **Microservices Architecture:** When data is scattered across multiple backend services, a GraphQL layer can act as an API Gateway, aggregating data from various sources into a single, unified, client-friendly API, simplifying frontend development.
*   **Developer Experience:** GraphQL's introspection capabilities, strong typing, and client-side tooling (like IDE plugins and client libraries) enhance developer productivity by providing clarity on available data and simplifying query construction.

By adopting GraphQL, our blogging platform can deliver a faster, more responsive user experience while providing frontend developers with unprecedented flexibility in data fetching, ultimately streamlining development and future iterations.