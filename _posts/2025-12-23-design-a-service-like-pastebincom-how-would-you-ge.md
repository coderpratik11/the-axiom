---
title: "Design a service like Pastebin.com. How would you generate unique, memorable URLs? How would you handle custom URLs, expiration of pastes, and syntax highlighting?"
date: 2025-12-23
categories: [System Design, Concepts]
tags: [interview, architecture, learning]
toc: true
layout: post
---

## 1. The Core Concept

Imagine you're trying to share a piece of code, a configuration file, or even just some plain text with a colleague. Email attachments can be cumbersome, and chat messages often strip formatting. This is where services like **Pastebin.com** shine. They provide a simple, web-based platform to share text snippets instantly.

> **Definition:** A **pastebin service** is an online application that allows users to store plain text or source code snippets, often for public viewing, and retrieve them via a unique URL. It acts as a temporary or permanent repository for text-based information.

At its heart, a pastebin service takes your text, saves it to a database, and gives you a short, unique URL to access it. It's like a digital notepad for sharing, designed for quick and dirty text distribution.

## 2. Deep Dive & Architecture

Designing a robust pastebin service involves several key architectural considerations, from URL generation to managing the lifecycle of a paste.

### 2.1. Unique, Memorable URL Generation

The URL is the primary identifier for a paste, so it must be both unique and easy to share.

#### **Approach 1: Incremental ID + Base62 Encoding**
This is a common strategy for generating short, unique identifiers.
1.  **Generate a Unique ID:** When a new paste is created, store it in a database (e.g., PostgreSQL, MySQL). The database's auto-incrementing primary key (`id`) serves as our unique identifier.
2.  **Encode to Base62:** Convert the numerical `id` into a base62 string. Base62 uses `0-9`, `a-z`, and `A-Z`, allowing for a compact representation.
    *   Example: An `id` of `12345` might become `3Vp` in base62.
    *   Formula: Similar to converting base10 to binary, but using 62 as the target base.
    python
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    BASE = len(ALPHABET)

    def encode_base62(num):
        if num == 0:
            return ALPHABET[0]
        arr = []
        while num > 0:
            rem = num % BASE
            arr.append(ALPHABET[rem])
            num //= BASE
        return "".join(arr[::-1])
    
    This method ensures uniqueness because the underlying `id` is unique. It's memorable because the URLs are short.

#### **Approach 2: Hashing or UUID**
Another approach is to generate a hash of the paste content or a UUID (Universally Unique Identifier).
*   **UUID:** Guarantees uniqueness across distributed systems, but generates long, non-memorable strings (e.g., `a1b2c3d4-e5f6-7890-1234-567890abcdef`).
*   **Hashing (e.g., SHA-256):** Generates a fixed-length hash of the content. While unique for unique content, it's long and doesn't handle tiny modifications well (different hash for "hello" vs "Hello"). A collision could also theoretically occur, though highly improbable for typical hash lengths.

> **Pro Tip:** For maximum memorability and user experience, start with a short base62 string (e.g., 6 characters). If a collision is detected (highly unlikely with database `id` as source), simply retry by using the next available `id`. For custom URLs, a dedicated check is needed.

### 2.2. Handling Custom URLs

Users often prefer to set their own short, descriptive URLs (e.g., `pastebin.com/my-project-bug`).

1.  **Validation:**
    *   **Length:** Limit the length (e.g., 3-20 characters).
    *   **Characters:** Restrict to alphanumeric and hyphens.
    *   **Reserved Keywords:** Prevent users from using reserved system keywords (e.g., `admin`, `api`, `login`).
2.  **Uniqueness Check:** Before creating the paste, query the database to ensure the desired custom URL is not already in use. This requires an index on the `url_key` column in your `Pastes` table.
3.  **Reservation:** If a custom URL is available, reserve it immediately (e.g., by creating a draft paste record with the chosen URL) to prevent race conditions where two users try to claim the same URL simultaneously.
4.  **Priority:** Custom URLs should take precedence over auto-generated ones. When a request comes for `/xyz`, first check for a custom URL `xyz`, then for an auto-generated one.

### 2.3. Expiration of Pastes

Pastes often have a "Time-To-Live" (TTL) to manage storage and privacy.

1.  **Storage:** Store an `expiration_date` (timestamp) in the `Pastes` table. If the paste never expires, this field can be `NULL` or a very distant future date.
2.  **Indexing:** Create a database index on the `expiration_date` column to efficiently query for expired pastes.
    sql
    CREATE INDEX idx_pastes_expiration_date ON Pastes (expiration_date);
    
3.  **Background Cleanup Job:**
    *   **Cron Job:** A scheduled task (e.g., daily or hourly) queries the database for pastes where `expiration_date < NOW()` and deletes them.
    *   **Message Queue (for scale):** For high-volume services, when a paste is created with an expiration, a message can be pushed to a queue (e.g., Kafka, RabbitMQ, SQS) with a delayed delivery/processing attribute set to the expiration time. A worker then processes these messages and deletes the corresponding paste.
    *   **TTL Index (NoSQL):** Databases like MongoDB and Redis offer native **TTL indexes** which automatically expire documents/keys after a specified time, simplifying cleanup logic.

> **Warning:** Deleting expired pastes should ideally be an asynchronous, background process to avoid impacting the user-facing application's performance.

### 2.4. Syntax Highlighting

Making code snippets readable is crucial. Syntax highlighting achieves this by applying different colors and styles to various elements of the code.

1.  **Language Detection:**
    *   **User Input:** Allow users to specify the language (e.g., "Python", "Java", "Markdown").
    *   **Auto-detection:** Use libraries (e.g., `linguist` for Ruby, `pygments` for Python) to guess the language based on content heuristics.
2.  **Highlighting Engine:**
    *   **Server-Side:** Use a library like `Pygments` (Python), `highlight.js` (Node.js), or `Rouge` (Ruby) on the backend. When a paste is created or viewed, the server processes the plain text and generates HTML with embedded `<span>` tags for styling. This HTML can then be served directly.
    *   **Client-Side:** Store the raw paste content and the detected language. The browser then uses a JavaScript library like `highlight.js` or `Prism.js` to perform highlighting client-side.
3.  **Storage:**
    *   Store the raw paste content.
    *   Store the detected/chosen `language` (e.g., "python", "javascript").
    *   Optionally, cache the pre-rendered HTML for server-side highlighting to reduce processing on subsequent views.

html
<!-- Example of client-side highlighting with highlight.js -->
<pre><code class="language-python">
def hello_world():
    print("Hello, Pastebin!")
</code></pre>
<script src="/path/to/highlight.min.js"></script>
<script>hljs.highlightAll();</script>


## 3. Comparison / Trade-offs

Let's compare the two primary approaches for **Syntax Highlighting**: Client-Side vs. Server-Side.

| Feature / Aspect          | Client-Side Highlighting (e.g., `highlight.js`)          | Server-Side Highlighting (e.g., `Pygments`)           |
| :------------------------ | :-------------------------------------------------------- | :---------------------------------------------------- |
| **Processing Location**   | User's browser                                            | Application server                                    |
| **Initial Page Load**     | Faster (raw content delivered, then highlighted by JS)    | Slower (server processes, then delivers full HTML)    |
| **CPU Usage**             | Offloaded to client machines                              | Consumes server CPU resources                         |
| **Maintenance/Updates**   | Easier to update (deploy new JS files)                    | Requires server-side redeployments (new libraries)    |
| **SEO Impact**            | Potentially weaker (content rendered post-load, bots might miss styles) | Stronger (fully rendered HTML, good for bots)         |
| **Network Payload**       | Smaller initial HTML, then JS/CSS for highlighting        | Larger HTML payload (pre-rendered styles)             |
| **User Experience**       | Possible FOUC (Flash of Unstyled Content) if JS is slow | Consistent styling, no FOUC                             |
| **Complexity**            | Simpler server logic, more client-side dependencies       | More complex server logic, less client-side runtime   |

For a service like Pastebin, which prioritizes speed and might have many concurrent views, a **hybrid approach** is often best:
*   **Server-side highlighting for popular languages** and initial page load to ensure good SEO and fast first paint.
*   **Client-side fallback/enhancement** for less common languages or dynamic theme changes.
*   **Caching** the highlighted output to reduce server load.

## 4. Real-World Use Case

Pastebin-like services are ubiquitous in the developer ecosystem and beyond.

*   **Debugging & Collaboration (Developers):** Developers frequently use them to share error logs, code snippets, or configuration files with colleagues or online communities (e.g., Stack Overflow) to get help or demonstrate issues. The ability to quickly share and review code without committing it to a version control system is invaluable.
*   **Temporary Notes & Information Sharing (General Users):** Beyond code, people use them to temporarily store and share plain text, shopping lists, meeting notes, or any information that needs to be distributed quickly and widely via a URL, without the need for an account or complex sharing permissions.
*   **Security Research & Incident Response:** Security professionals sometimes use pastebins to quickly share indicators of compromise (IOCs), exploit code samples (often anonymized), or vulnerability details for rapid analysis within a trusted group.
*   **Internal Tools:** Many companies build internal pastebin services for their employees to share code snippets, internal documentation, or temporary configurations within a secure environment.

The "why" behind their use is simple: **efficiency and accessibility**. They strip away the complexities of email attachments, file hosting services, or dedicated collaboration platforms, offering a frictionless way to share text-based information instantly. This ease of use makes them a foundational tool in many digital workflows.