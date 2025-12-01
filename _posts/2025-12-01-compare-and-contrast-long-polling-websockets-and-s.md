---
title: "Compare and contrast Long Polling, WebSockets, and Server-Sent Events (SSE). For a live stock ticker application, which technology would you choose and why?"
date: 2025-12-01
categories: [System Design, Real-time Communication]
tags: [long polling, websockets, sse, real-time, system design, architecture, web development, interview, learning]
toc: true
layout: post
---

In the modern web, users expect dynamic, up-to-the-second information. From social media feeds to collaborative documents and financial tickers, **real-time communication** is a cornerstone of engaging user experiences. Achieving this responsiveness, however, requires careful consideration of underlying technologies. This post dives into three prominent techniques: **Long Polling**, **Server-Sent Events (SSE)**, and **WebSockets**, comparing their mechanics, trade-offs, and suitability for a high-stakes application like a live stock ticker.

## 1. The Core Concept

Imagine you're waiting for an important delivery. How do you know when it arrives?

*   **Long Polling** is like calling the delivery company, asking "Is my package here yet?". Instead of hanging up if it's not ready, they put you on hold and promise to notify you as soon as it arrives (or after a set time if it's delayed). Once they tell you, you immediately call them back and get on hold again.
*   **Server-Sent Events (SSE)** is akin to subscribing to a news feed. Once you subscribe, the news agency continuously sends you updates as soon as they happen, without you needing to ask each time. However, you can't send news back to them.
*   **WebSockets** is like establishing a dedicated, two-way telephone line with the delivery company. Once connected, you can both talk to each other freely and continuously, sending and receiving updates at any time.

> **Definition: Real-time Communication**
> Real-time communication refers to the ability for a client and server to exchange data with minimal latency, often pushing updates from the server to the client without the client explicitly requesting them. This creates a highly responsive and dynamic user experience.

## 2. Deep Dive & Architecture

Each method tackles the challenge of real-time communication differently, impacting their performance, complexity, and ideal use cases.

### 2.1. Long Polling

**Long Polling** is an adaptation of traditional **HTTP polling**. Instead of the client repeatedly asking the server for updates at fixed intervals (short polling), with long polling, the client makes an HTTP request, and the server **holds the connection open** until new data is available or a timeout occurs. Once data is sent (or the timeout is reached), the server closes the connection. The client then immediately opens a new request to repeat the process.

*   **Mechanism**: Uses standard HTTP GET requests.
*   **Connection**: Each update requires a new HTTP connection and full request/response cycle.
*   **Server Burden**: Servers must keep many connections open concurrently, even if idle.

javascript
function longPollForUpdates() {
    fetch('/api/updates')
        .then(response => {
            if (response.status === 200) {
                return response.json();
            } else {
                throw new Error('Server error');
            }
        })
        .then(data => {
            console.log('Received update:', data);
            // Process the data (e.g., update UI)
            longPollForUpdates(); // Immediately make the next request
        })
        .catch(error => {
            console.error('Long polling error:', error);
            // Implement backoff or retry logic on error
            setTimeout(longPollForUpdates, 5000); 
        });
}

// Initial call to start the polling
longPollForUpdates();


> **Warning:** While seemingly simple, Long Polling can be resource-intensive on the server due to numerous open connections and repeated HTTP header overhead. Latency can also be higher than other methods as each update still involves initiating a new request.

### 2.2. Server-Sent Events (SSE)

**Server-Sent Events (SSE)** provide a **unidirectional** communication channel from the server to the client over a standard HTTP connection. The client initiates a request, and the server keeps the connection open indefinitely, sending data as a stream of events.

*   **Mechanism**: Uses standard HTTP/1.1 or HTTP/2. The server sets the `Content-Type` header to `text/event-stream`.
*   **Connection**: A single, persistent HTTP connection for server-to-client data flow.
*   **Automatic Reconnection**: Browsers have built-in support for automatically re-establishing the connection if it's dropped.
*   **Data Format**: Limited to UTF-8 text data.
*   **API**: Uses the browser's `EventSource` API.

javascript
// Client-side
const eventSource = new EventSource('/api/stock-updates');

eventSource.onopen = () => {
    console.log('SSE connection opened.');
};

eventSource.onmessage = (event) => {
    // Data is always a string, typically JSON
    const data = JSON.parse(event.data);
    console.log('Received stock update:', data);
    // Update UI with new stock price
};

eventSource.onerror = (error) => {
    console.error('SSE Error:', error);
    // The browser automatically attempts to reconnect
};

eventSource.addEventListener('trade', (event) => {
    // Custom event type 'trade'
    console.log('Trade alert:', JSON.parse(event.data));
});

// To close the connection explicitly:
// eventSource.close();


javascript
// Server-side (Conceptual example with Node.js/Express)
app.get('/api/stock-updates', (req, res) => {
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    });

    const sendStockUpdate = () => {
        const price = (Math.random() * 1000).toFixed(2);
        const symbol = ['AAPL', 'GOOG', 'MSFT'][Math.floor(Math.random() * 3)];
        const update = { symbol, price, timestamp: new Date().toISOString() };
        // SSE data format: data: [your_data]\n\n
        res.write(`data: ${JSON.stringify(update)}\n\n`); 
    };

    const intervalId = setInterval(sendStockUpdate, 1000); // Send update every second

    req.on('close', () => {
        clearInterval(intervalId);
        res.end();
        console.log('Client disconnected from SSE.');
    });
});


### 2.3. WebSockets

**WebSockets** provide a **full-duplex**, persistent communication channel between a client and a server over a single TCP connection. It starts as an HTTP request, which then "upgrades" to a WebSocket connection through a handshake process. Once upgraded, the connection uses its own **WebSocket protocol**, allowing messages to be sent in either direction with minimal overhead.

*   **Mechanism**: Initiates with an HTTP/1.1 handshake (`Upgrade` header), then switches to the `ws://` or `wss://` protocol.
*   **Connection**: A single, long-lived TCP connection.
*   **Communication**: Bidirectional (server-to-client and client-to-server).
*   **Data Format**: Supports both text (UTF-8) and binary data frames.
*   **API**: Uses the browser's `WebSocket` API.
*   **Complexity**: Requires a dedicated WebSocket server or a server-side framework that supports WebSockets.

javascript
// Client-side
const ws = new WebSocket('ws://localhost:8080/stock-feed'); // Use wss:// for secure connections

ws.onopen = () => {
    console.log('WebSocket connection opened!');
    ws.send(JSON.stringify({ type: 'subscribe', symbol: 'AAPL' })); // Send subscription request
};

ws.onmessage = (event) => {
    // Received data can be text or binary
    const data = JSON.parse(event.data);
    console.log('Received stock update via WebSocket:', data);
    // Update UI with new stock price
};

ws.onclose = (event) => {
    console.log('WebSocket disconnected:', event.reason, event.code);
    // Implement client-side reconnection logic as it's not built-in
    setTimeout(() => {
        console.log('Attempting to reconnect...');
        // re-establish WebSocket connection
    }, 3000);
};

ws.onerror = (error) => {
    console.error('WebSocket Error:', error);
};

// To send data from client to server:
// ws.send('Hello Server!');
// ws.send(new ArrayBuffer(10)); // Send binary data


## 3. Comparison / Trade-offs

Choosing the right technology depends heavily on the specific requirements of your application. The table below summarizes the key differences:

| Feature             | Long Polling                                       | Server-Sent Events (SSE)                        | WebSockets                                     |
| :------------------ | :------------------------------------------------- | :---------------------------------------------- | :--------------------------------------------- |
| **Communication**   | Unidirectional (client initiated poll)             | Unidirectional (server push)                    | Bidirectional (full-duplex)                    |
| **Protocol**        | Standard HTTP/1.x                                  | Standard HTTP/1.x (uses `text/event-stream`)    | WS (upgraded from HTTP)                        |
| **Connection**      | Short-lived, new connection for each update        | Single, persistent HTTP connection              | Single, persistent TCP connection              |
| **Overhead**        | High (full HTTP headers per update)                | Low (minimal headers after handshake)           | Very Low (lightweight framing after handshake) |
| **Browser Support** | Universal (standard HTTP)                          | Excellent (modern browsers)                     | Excellent (modern browsers)                    |
| **Complexity**      | Moderate (client re-initiation logic)              | Low (simple `EventSource` API, auto-reconnect)  | Moderate-High (dedicated server, client reconnect logic) |
| **Data Format**     | Any (JSON, XML, etc.)                              | UTF-8 text only                                 | Any (text, binary)                             |
| **Use Case**        | Low-frequency updates, compatibility with legacy systems, firewalls | Real-time server-to-client updates (e.g., news feeds, stock tickers, dashboards) | Real-time interactive apps (chat, gaming, collaborative editing, complex IoT) |
| **Scalability**     | Challenging (many open-but-idle connections)       | Good (efficient use of HTTP, connection-based)  | Excellent (efficient, less overhead per message, designed for high concurrency) |
| **Firewall/Proxy**  | Generally compatible                               | Generally compatible                            | Can sometimes be blocked by strict firewalls/proxies |

> **Pro Tip:** When making your decision, prioritize the **direction of communication** (one-way vs. two-way), the **frequency and volume of data**, and the **complexity** you're willing to manage on both client and server sides. Don't immediately jump to WebSockets if a simpler solution like SSE fits your needs.

## 4. Real-World Use Case: Live Stock Ticker Application

For a **live stock ticker application**, the primary requirement is to deliver **frequent, low-latency updates** of stock prices from the server to many clients. While clients might filter or display specific stocks, the core data flow is overwhelmingly **unidirectional** from server to client.

Let's evaluate our options for this specific scenario:

1.  **Long Polling**: This would be a poor choice. The high frequency of stock price updates would lead to constant connection establishment and tear-down, generating significant HTTP overhead and latency. It's not suitable for truly "live" updates.
2.  **WebSockets**: An excellent and highly capable option. Its full-duplex nature allows clients to easily subscribe to specific stocks (`ws.send('subscribe:AAPL')`) and receive updates efficiently. The low overhead per message and persistent connection make it ideal for high-volume, low-latency data streams. If the application also involved interactive trading or complex client-to-server messaging, WebSockets would be the clear winner.
3.  **Server-Sent Events (SSE)**: Also an excellent option, and arguably a more pragmatic fit for the *core* "live stock ticker" functionality. SSE is designed precisely for streaming unidirectional data from the server to clients. It leverages standard HTTP, benefits from built-in browser reconnection, and is simpler to implement than WebSockets.

### Which technology would I choose and why?

For a pure **live stock ticker application** where the primary goal is displaying real-time price updates and client interaction is limited to basic display preferences (e.g., filtering stocks locally), I would choose **Server-Sent Events (SSE)**.

Here's why SSE is my preferred choice for this specific scenario:

*   **Unidirectional Fit**: A stock ticker's fundamental need is to receive updates from the server. SSE is purpose-built for efficient, unidirectional server-to-client streaming, perfectly matching this requirement.
*   **Simplicity and Ease of Implementation**: SSE is significantly simpler to implement than WebSockets. It uses the standard `EventSource` API in the browser and requires less specialized server-side infrastructure compared to a full WebSocket server. This means faster development cycles and reduced maintenance overhead.
*   **Automatic Reconnection**: Browsers automatically handle reconnection attempts for SSE if the connection is dropped due to network issues. This is a crucial feature for a real-time application where continuous updates are expected, enhancing robustness without requiring complex client-side logic.
*   **HTTP Compatibility**: Being built on HTTP, SSE can traverse many existing network proxies and firewalls without issues, unlike WebSockets which can sometimes face stricter blocking policies.

> **Consideration for WebSockets**: If the "stock ticker application" were part of a larger, interactive **trading platform** where users actively place trades, manage complex subscriptions to *hundreds* of different financial instruments, or require other forms of frequent client-to-server communication (e.g., real-time order book updates based on client actions), then **WebSockets would be the superior choice**. Its bidirectional nature and more efficient framing would justify the increased complexity.

However, for a dedicated "live stock ticker" as described, where the flow is predominantly server-to-client data push, **SSE offers the optimal balance of functionality, performance, and simplicity.** It provides a robust, low-latency stream without the added complexity of a full-duplex protocol if that capability isn't strictly necessary.