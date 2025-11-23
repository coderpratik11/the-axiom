---
title: "Design the REST API endpoints for a simple blogging platform (Users, Posts, Comments). Specify the HTTP verbs and URL structures."
date: 2025-11-23
categories: [System Design, API Design]
tags: [rest, api, http, design, blogging, interview, architecture, learning]
toc: true
layout: post
---

## 1. The Core Concept

Imagine you're running a highly organized library. Instead of just shouting requests across the room, you have a set of clear rules:
- You go to a specific section (e.g., "Fiction Books," "Reference Journals").
- You perform a specific action (e.g., "borrow," "return," "check availability," "add a new book").
- You might specify which exact book you're interested in (e.g., "the specific copy of '1984'").

This library system is a great analogy for a **REST API**. It's a structured way for different software systems to communicate and perform actions on **resources**.

> **Pro Tip:**
> **REST (Representational State Transfer)** is an architectural style for designing networked applications. It defines a set of constraints that, when applied, yield a distributed system with desirable properties such as performance, scalability, and modifiability. It primarily leverages HTTP methods to interact with **resources** identified by **URIs**.

In our blogging platform, the "resources" will be `Users`, `Posts`, and `Comments`. Our goal is to design a clear, predictable, and scalable way for clients (web browsers, mobile apps) to interact with these resources.

## 2. Deep Dive & Architecture

Designing REST API endpoints involves identifying your resources, assigning unique **URIs (Uniform Resource Identifiers)** to them, and determining which **HTTP verbs** (methods) can be used to perform operations on those resources.

### 2.1 Key REST Principles

Before diving into endpoints, let's briefly recall the core principles:

-   **Resources:** Everything is a resource (e.g., a user, a post, a comment).
-   **URIs:** Each resource or collection of resources has a unique identifier (e.g., `/users`, `/posts/123`).
-   **HTTP Verbs:** Standardized actions (GET, POST, PUT, PATCH, DELETE) are used to manipulate resources.
-   **Statelessness:** Each request from a client to the server must contain all the information needed to understand the request. The server doesn't store any client context between requests.
-   **Uniform Interface:** A consistent way of interacting with different resources.

### 2.2 Designing Endpoints for a Blogging Platform

We'll define endpoints for `Users`, `Posts`, and `Comments`. We'll use plural nouns for collections and identifiers (like `{id}`) for specific resources.

#### 2.2.1 User Endpoints

| HTTP Verb | URI                         | Description                           | Example Request Body                                    |
| :-------- | :-------------------------- | :------------------------------------ | :------------------------------------------------------ |
| `POST`    | `/users`                    | **Create** a new user                 | `{"username": "johndoe", "email": "john@example.com"}` |
| `GET`     | `/users`                    | **Retrieve** a list of all users      | -                                                       |
| `GET`     | `/users/{id}`               | **Retrieve** a specific user by ID    | -                                                       |
| `PUT`     | `/users/{id}`               | **Update** a user (full replacement)  | `{"username": "jd", "email": "jd@example.com"}`         |
| `PATCH`   | `/users/{id}`               | **Partially Update** a user           | `{"email": "john.doe@example.com"}`                     |
| `DELETE`  | `/users/{id}`               | **Delete** a specific user            | -                                                       |

#### 2.2.2 Post Endpoints

| HTTP Verb | URI                         | Description                           | Example Request Body                                      |
| :-------- | :-------------------------- | :------------------------------------ | :-------------------------------------------------------- |
| `POST`    | `/posts`                    | **Create** a new post                 | `{"title": "My New Post", "content": "Hello World!", "authorId": 1}` |
| `GET`     | `/posts`                    | **Retrieve** a list of all posts      | -                                                         |
| `GET`     | `/posts/{id}`               | **Retrieve** a specific post by ID    | -                                                         |
| `PUT`     | `/posts/{id}`               | **Update** a post (full replacement)  | `{"title": "Updated Title", "content": "New content."}`   |
| `PATCH`   | `/posts/{id}`               | **Partially Update** a post           | `{"content": "Even newer content."}`                      |
| `DELETE`  | `/posts/{id}`               | **Delete** a specific post            | -                                                         |

> **Pro Tip: Pagination, Filtering, and Sorting**
> For collections, you'll often need to handle large datasets. This is typically done via query parameters:
> -   **Pagination:** `GET /posts?page=2&limit=10`
> -   **Filtering:** `GET /posts?authorId=1&status=published`
> -   **Sorting:** `GET /posts?sort=createdAt_desc`

#### 2.2.3 Comment Endpoints (Nested Resources)

Comments are typically related to a specific post. A **nested resource** approach (`/posts/{post_id}/comments`) clearly signifies this relationship.

| HTTP Verb | URI                                     | Description                               | Example Request Body                            |
| :-------- | :-------------------------------------- | :---------------------------------------- | :---------------------------------------------- |
| `POST`    | `/posts/{post_id}/comments`             | **Create** a new comment for a post       | `{"content": "Great post!", "authorId": 2}`    |
| `GET`     | `/posts/{post_id}/comments`             | **Retrieve** all comments for a post      | -                                               |
| `GET`     | `/posts/{post_id}/comments/{comment_id}` | **Retrieve** a specific comment for a post | -                                               |
| `PUT`     | `/posts/{post_id}/comments/{comment_id}` | **Update** a comment (full replacement)   | `{"content": "Really great post!"}`             |
| `PATCH`   | `/posts/{post_id}/comments/{comment_id}` | **Partially Update** a comment            | `{"content": "Awesome post!"}`                  |
| `DELETE`  | `/posts/{post_id}/comments/{comment_id}` | **Delete** a specific comment             | -                                               |

### 2.3 HTTP Status Codes

Responses from a REST API should always include an appropriate HTTP status code to indicate the outcome of the request.

-   `200 OK`: General success for `GET`, `PUT`, `PATCH`, `DELETE`.
-   `201 Created`: Resource successfully created (typically for `POST`).
-   `204 No Content`: Successful request, but no response body (e.g., successful `DELETE`).
-   `400 Bad Request`: Client-side error (e.g., invalid input).
-   `401 Unauthorized`: Authentication required or failed.
-   `403 Forbidden`: Authenticated, but client doesn't have permission.
-   `404 Not Found`: Resource not found.
-   `500 Internal Server Error`: Server-side error.

json
// Example of a successful GET /posts/{id} response
{
  "id": 123,
  "title": "My Awesome Blog Post",
  "content": "This is the content of my post.",
  "author": {
    "id": 1,
    "username": "johndoe"
  },
  "createdAt": "2023-10-26T10:00:00Z",
  "updatedAt": "2023-10-26T10:30:00Z"
}

// Example of a 201 Created POST /posts response
// The Location header would typically point to the new resource: /posts/124
{
  "id": 124,
  "title": "Newly Created Post",
  "content": "This post was just made.",
  "author": {
    "id": 1,
    "username": "johndoe"
  },
  "createdAt": "2023-10-26T11:00:00Z",
  "updatedAt": "2023-10-26T11:00:00Z"
}

// Example of a 404 Not Found response
{
  "status": 404,
  "error": "Not Found",
  "message": "The requested post with ID 999 was not found."
}


## 3. Comparison / Trade-offs

When designing APIs, the RESTful approach isn't the only one, but it's a widely adopted standard. Let's compare it with a more **RPC (Remote Procedure Call)-style** approach, which focuses on exposing functions or actions rather than resources.

| Feature             | RESTful API Design (Resource-Oriented)                       | RPC-Style API Design (Action-Oriented)                       |
| :------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- |
| **Focus**           | **Resources** and their state. Operates on nouns.            | **Actions** or functions. Operates on verbs.                 |
| **URI Structure**   | Plural nouns for collections, IDs for specific resources. Hierarchical. <br> `GET /posts/123` | Often includes verbs in the URI, less structured. <br> `GET /getPost?id=123` or `POST /createPost` |
| **HTTP Verbs Use**  | Leverages standard HTTP methods (GET, POST, PUT, PATCH, DELETE) for **CRUD** operations. | Often primarily uses `POST` for all operations, with the action specified in the URI or body. |
| **Statelessness**   | Naturally stateless; each request is self-contained.         | Can be stateless, but the nature of specific procedures can sometimes lead to stateful designs. |
| **Cacheability**    | Easily cacheable (e.g., `GET` requests).                    | Less inherently cacheable as actions can have side effects.   |
| **Discoverability** | Highly discoverable; standard verbs and predictable URIs make it easy to understand. | Less discoverable; requires explicit documentation of each function. |
| **Flexibility**     | Good for general CRUD on resources. Can sometimes be awkward for complex, non-CRUD operations. | Excellent for highly specific, complex operations that don't map cleanly to CRUD. |
| **Complexity**      | Clear and predictable for standard operations.               | Can lead to many custom endpoints, potentially increasing complexity over time. |

> **Warning:**
> While REST is powerful, it's not a silver bullet. For highly complex, graph-like data requirements, or real-time communication, alternatives like GraphQL or WebSockets might be more suitable. However, for a standard blogging platform's CRUD operations, REST remains an excellent choice.

## 4. Real-World Use Case

REST APIs are the backbone of the modern web. From social media platforms to e-commerce giants and cloud infrastructure providers, you'd be hard-pressed to find a major service that doesn't expose at least some of its functionality via REST.

### Example: Twitter API

Consider the **Twitter API**. It's a classic example of a RESTful service that allows developers to interact with Twitter's data programmatically.

-   **Users:**
    -   `GET /2/users/:id` - Get a user by ID
    -   `GET /2/users/by/username/:username` - Get a user by username
-   **Tweets (Posts):**
    -   `POST /2/tweets` - Create a Tweet
    -   `GET /2/tweets` - Get a list of Tweets (e.g., a user's timeline)
    -   `GET /2/tweets/:id` - Get a specific Tweet
    -   `DELETE /2/tweets/:id` - Delete a Tweet
-   **Liking (a form of "Comment" or interaction):**
    -   `POST /2/users/:id/likes` - Like a Tweet
    -   `DELETE /2/users/:id/likes/:tweet_id` - Unlike a Tweet

### Why REST is so Widely Used

1.  **Interoperability:** REST APIs allow different clients (web apps, mobile apps, desktop apps, other backend services) written in various programming languages to communicate seamlessly with a single backend service. This is critical for ecosystems like Twitter, where countless third-party applications integrate with their platform.
2.  **Scalability:** The stateless nature of REST allows for easy scaling. Any server can handle any request, simplifying load balancing and distributed architectures. When Twitter faces massive spikes in traffic during major events, this scalability is vital.
3.  **Simplicity and Standardization:** By leveraging existing HTTP standards and simple URI patterns, REST APIs are relatively easy to understand, develop, and maintain. This lowers the barrier to entry for developers and speeds up integration.
4.  **Decoupling:** REST promotes a clear separation of concerns between the client and the server. Clients don't need to know the server's internal implementation details, and servers don't need to store client state, leading to more robust and flexible systems.

In essence, REST provides a powerful, flexible, and universally understood language for building distributed systems, making it an indispensable tool for any modern software architect or engineer.