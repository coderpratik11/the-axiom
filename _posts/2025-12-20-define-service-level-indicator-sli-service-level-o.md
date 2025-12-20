---
title: "Define Service Level Indicator (SLI), Service Level Objective (SLO), and Service Level Agreement (SLA). Provide a practical example for an API endpoint (e.g., p99 latency < 200ms)."
date: 2025-12-20
categories: [System Design, Concepts]
tags: [interview, architecture, learning, observability, sre, reliability, monitoring]
toc: true
layout: post
---

## 1. The Core Concept

In the world of software and systems, ensuring reliability and performance is paramount. But how do we objectively measure and communicate whether a service is "reliable" or "performant"? This is where **Service Level Indicators (SLIs)**, **Service Level Objectives (SLOs)**, and **Service Level Agreements (SLAs)** come into play. They form a crucial framework for defining, measuring, and guaranteeing the quality of a service.

Imagine renting a car. You care about certain aspects: Is it available when I need it? Does it start every time? How fast does it accelerate? How much does it cost if it breaks down? These are analogous to the reliability of a software service.

> **Definition:**
> - A **Service Level Indicator (SLI)** is a quantifiable measure of some aspect of the service provided. It's *what* we measure.
> - A **Service Level Objective (SLO)** is a target value or range for an SLI that defines the desired level of service. It's *what we aim for*.
> - A **Service Level Agreement (SLA)** is a formal, contractual agreement between a service provider and a customer that specifies the SLOs and the penalties for not meeting them. It's *what we promise*.

## 2. Deep Dive & Architecture

Let's break down each component with technical detail and a practical example.

### 2.1. Service Level Indicator (SLI)

An **SLI** is a direct numerical measure of a service's health. It should be unambiguous, easy to measure, and reflect user experience.

#### Common SLI Examples:
*   **Latency:** The time it takes for a service to respond to a request. Often measured as percentiles (e.g., p50, p90, p99 latency).
*   **Error Rate:** The proportion of requests that result in an error (e.g., HTTP 5xx responses).
*   **Throughput:** The number of requests a service can handle per unit of time (e.g., requests per second, messages processed per minute).
*   **Availability:** The proportion of time a service is accessible and operational.

#### Measurement Example (Prometheus-like metric):
To measure latency for an API endpoint, you might instrument your code to track request durations:

go
import (
	"github.com/prometheus/client_golang/prometheus"
	"time"
)

var (
	httpRequestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "Duration of HTTP requests.",
			Buckets: prometheus.DefBuckets, // Default buckets: .005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10
		},
		[]string{"path", "method", "status_code"},
	)
)

func init() {
	prometheus.MustRegister(httpRequestDuration)
}

func handleRequest(path, method string, handler func()) {
	start := time.Now()
	// ... actual request processing ...
	handler() // Simulate request processing
	duration := time.Since(start).Seconds()

	// Assuming we determine status_code here, for example: "200" or "500"
	status_code := "200" 
	httpRequestDuration.WithLabelValues(path, method, status_code).Observe(duration)
}

// In your HTTP server:
// func MyAPIRouter(w http.ResponseWriter, r *http.Request) {
//     handleRequest("/api/v1/users/{id}", "GET", func() {
//         // Your handler logic here
//     })
// }

This `httpRequestDuration` metric could then be queried to derive various percentiles of latency.

### 2.2. Service Level Objective (SLO)

An **SLO** sets a clear target for an SLI over a specific period. It transforms a raw measurement into an actionable goal. SLOs are typically set internally by engineering or SRE teams, often in conjunction with product managers, to define acceptable performance and reliability.

#### Key aspects of an SLO:
*   **Specific SLI:** Which metric are we targeting?
*   **Target Value:** What is the desired threshold?
*   **Time Window:** Over what period must the target be met? (e.g., 7 days, 28 days, 30 days rolling window).
*   **Compliance:** The percentage of the time window the target must be met (e.g., 99.9% of requests).

#### The Importance of Error Budgets:
SLOs introduce the concept of an **Error Budget**. If an SLO states that a service should be available 99.9% of the time, the remaining 0.1% is the "error budget." This budget represents the acceptable amount of downtime or degraded performance over the measurement period. When the service exceeds its error budget, it indicates a failure to meet the SLO, triggering alerts and prioritizing reliability work over new feature development.

### 2.3. Service Level Agreement (SLA)

An **SLA** is a formal contract between a service provider and its customer. It builds upon SLOs by defining the consequences, usually financial, if the SLOs are not met. SLAs are typically less stringent than internal SLOs, providing a buffer before penalties are incurred.

#### Key aspects of an SLA:
*   **Formal Document:** A legally binding agreement.
*   **Defined SLOs:** Specifies the exact SLIs and their target values.
*   **Penalties/Remedies:** What happens if the service fails to meet the specified SLOs (e.g., service credits, refunds).
*   **Exclusions:** Conditions under which the SLA does not apply (e.g., customer-initiated configuration errors, force majeure).

> **Pro Tip:** Your internal SLOs should almost always be more aggressive than your external SLAs. This gives your team an internal buffer, so you have time to react and fix issues before breaching the customer-facing SLA and incurring penalties.

### 2.4. Practical Example: User Profile API Endpoint

Let's apply these concepts to a common API endpoint: `GET /api/v1/users/{id}` (to fetch a user's profile).

#### **1. Service Level Indicators (SLIs)** for `/api/v1/users/{id}`:

*   **Latency:** The time taken for the API to respond to a request.
*   **Error Rate:** The percentage of requests that return a 5xx HTTP status code.
*   **Availability:** The percentage of successful requests (2xx/3xx/4xx codes) vs. total requests. (Note: 4xx errors are often considered valid client errors, not service errors, for availability SLIs).

#### **2. Service Level Objectives (SLOs)** for `/api/v1/users/{id}`:

*   **Latency SLO:** `p99 latency < 200ms` for 99% of requests over a 7-day rolling window. (Meaning, 99% of requests must complete within 200ms, and this must hold true for 99% of the 7-day period).
*   **Error Rate SLO:** `Error Rate < 0.1%` (i.e., less than 1 in 1000 requests return a 5xx error) over a 7-day rolling window.
*   **Availability SLO:** `99.95% Availability` (i.e., 99.95% of requests result in a non-5xx status code) over a 7-day rolling window.

#### **3. Service Level Agreement (SLA)** for `/api/v1/users/{id}` (hypothetical for an external customer):

*   **Availability SLA:** "The API will be available 99.9% of the time over a calendar month. If availability falls below 99.9%, the customer will receive a service credit of 10% of their monthly subscription fee for each 0.1% drop below the threshold, up to a maximum of 50%."
*   **Latency SLA (less common to contractually guarantee but can be included):** "The P99 latency for read operations (like `GET /api/v1/users/{id}`) will not exceed 500ms for more than 1% of total requests measured over a calendar month. Breaches will be reported, but no direct financial penalty applies."

Notice how the internal SLOs (99.95% availability, p99 latency < 200ms) are stricter than the external SLA (99.9% availability, p99 latency < 500ms). This gives the engineering team an **error budget** (0.05% for availability) to work with before risking an SLA breach.

## 3. Comparison / Trade-offs

Understanding the distinct roles of SLI, SLO, and SLA is critical. Here's a comparison:

| Feature          | Service Level Indicator (SLI)                                | Service Level Objective (SLO)                                  | Service Level Agreement (SLA)                                     |
| :--------------- | :----------------------------------------------------------- | :------------------------------------------------------------- | :---------------------------------------------------------------- |
| **What it is**   | A quantifiable metric indicating service performance.        | A target value or range for an SLI over a specific period.     | A formal contract stating SLOs and penalties for breaches.        |
| **Who defines it** | Engineering/Operations teams, guided by user experience.     | Engineering/SRE teams, Product Management, Business Stakeholders. | Service Provider and Customer (legal teams involved).             |
| **Focus**        | Raw data, factual measurement of service health.             | Desired level of service, internal performance target.         | External commitment, legal obligation, customer assurance.        |
| **Contractual?** | No.                                                          | No, but forms the basis of internal operational targets.       | Yes, a legally binding document.                                  |
| **Granularity**  | Very granular (individual requests, specific events).        | Aggregated over a time window (e.g., 7 days, 30 days).         | Aggregated over longer periods (e.g., monthly, quarterly).        |
| **Primary Audience** | Engineers, monitoring systems.                               | Engineers, SREs, Product Managers.                             | Customers, Account Managers, Legal Teams.                         |
| **Example**      | `HTTP 200 responses / Total HTTP responses`                  | `Availability > 99.95% over 7 days`                            | `99.9% monthly uptime, 10% credit for breaches`                   |
| **Action**       | Monitor, graph, alert.                                       | Drive engineering effort, manage error budget, trigger alerts. | Trigger legal or financial repercussions, customer communication. |

## 4. Real-World Use Case

SLIs, SLOs, and SLAs are foundational to **Site Reliability Engineering (SRE)** practices and are widely adopted across the tech industry, especially in companies managing large-scale, critical services.

*   **Google's SRE Handbook:** Google pioneered much of the modern SRE discipline, emphasizing SLOs as the primary tool for balancing reliability and feature velocity. They use aggressive internal SLOs to guide engineering decisions, allocate resources, and determine when to halt new feature development to focus on reliability.
*   **Cloud Providers (AWS, Azure, GCP):** These providers publish extensive SLAs for their various services (EC2, S3, SQS, etc.). For instance, AWS S3 might offer "99.999999999% (11 nines) durability" and "99.99% availability" SLAs. Customers depend on these to build their own reliable systems on top.
*   **SaaS Companies (Netflix, Salesforce, etc.):** Any company offering a service to external customers uses this framework. Netflix, for example, sets high internal SLOs for streaming availability and performance to ensure a seamless user experience, which in turn influences their business metrics and customer retention.

#### The "Why": Driving Reliability and Customer Satisfaction

These concepts are indispensable because they:
*   **Provide Clarity:** Define what "good" looks like for a service, removing ambiguity.
*   **Align Teams:** Bridge the gap between engineering (what's possible) and business (what's needed) by setting measurable, shared goals.
*   **Guide Prioritization:** With an error budget, teams can make data-driven decisions on when to prioritize reliability work over new features. This prevents perpetual feature development at the expense of stability.
*   **Manage Expectations:** For customers, SLAs clearly communicate what level of service they can expect and what recourse they have if that level isn't met.
*   **Improve Observability:** The act of defining SLIs forces teams to instrument their systems effectively, leading to better monitoring and a deeper understanding of their service's behavior.

By meticulously defining and tracking SLIs, setting ambitious yet achievable SLOs, and establishing clear SLAs, organizations can build more resilient systems, foster better communication, and ultimately deliver superior experiences to their users.