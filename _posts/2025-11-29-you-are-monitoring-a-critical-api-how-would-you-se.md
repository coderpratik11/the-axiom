---
title: "You are monitoring a critical API. How would you set up an alerting system to notify the on-call engineer if the p99 latency exceeds 500ms or the error rate goes above 1%?"
date: 2025-11-29
categories: [System Design, Monitoring]
tags: [alerting, monitoring, observability, apm, slos, slas, reliability]
toc: true
layout: post
---

As a Principal Software Engineer, ensuring the reliability and performance of critical APIs is paramount. A momentary lapse in performance or an increase in errors can lead to frustrated users, lost revenue, and significant reputational damage. This post will detail how to construct a robust alerting system specifically designed to catch deviations in p99 latency and error rates for your most critical APIs.

## 1. The Core Concept

Imagine your critical API as a bustling express delivery service. Every package (API request) needs to arrive quickly and correctly. You don't just care about the average delivery time, because a few very slow deliveries can still ruin customer experience. You also care deeply if packages are consistently being damaged or lost.

**Monitoring** is like having sensors on every truck and delivery person, constantly reporting their status. **Alerting** is the immediate alarm that sounds when those sensors detect something is wrong – a truck is stuck in traffic, or a package was incorrectly delivered. It’s about being proactive, not reactive, and ensuring the right person is notified instantly to resolve the issue.

> **Alerting** is the act of notifying a designated individual or team when a system metric crosses a predefined threshold, indicating a potential issue requiring immediate attention. For critical APIs, this often means setting up alerts for **Service Level Objectives (SLOs)** related to latency, error rates, and availability.

## 2. Deep Dive & Architecture

Setting up an effective alerting system involves several key architectural components working in concert. For our specific scenario – p99 latency exceeding 500ms or error rate above 1% – we need robust data collection, intelligent thresholding, and reliable notification delivery.

### 2.1. Metrics Collection

The first step is gathering the right data. For an API, this typically involves:

*   **Latency Metrics:** Recording the duration of each API request.
*   **Success/Error Metrics:** Recording whether an API request succeeded or failed (e.g., HTTP 2xx vs. 4xx/5xx status codes).

There are several ways to collect these:

*   **Application Performance Monitoring (APM) Tools:** Services like Datadog, New Relic, Dynatrace, or AppDynamics automatically instrument your code to collect detailed metrics, including latency percentiles (like p99) and error counts.
*   **Service Mesh:** Technologies like Istio or Linkerd can collect request-level metrics (latency, error codes) at the network layer, independent of the application code.
*   **Custom Instrumentation:** Using client libraries for time-series databases (e.g., Prometheus client libraries, Micrometer for Spring Boot) to emit metrics directly from your application code.

### 2.2. Metrics Storage & Processing

Once collected, metrics need to be stored in a system optimized for time-series data and queryable for aggregation and threshold evaluation.

*   **Time-Series Databases (TSDB):**
    *   **Prometheus:** A popular open-source monitoring system that pulls metrics from instrumented targets. It's excellent for storing and querying metrics with a powerful query language (PromQL).
    *   **Cloud-Native Options:** AWS CloudWatch, Google Cloud Monitoring, Azure Monitor provide managed time-series storage and alerting capabilities.
    *   **Commercial APM Backends:** The APM tools mentioned earlier (Datadog, New Relic) have their own highly optimized backends.

**Why p99 Latency?**
The **p99 (99th percentile) latency** means that 99% of requests complete within that time, while 1% of requests take longer. This is a critical metric because:
*   **It captures the "tail" latency:** Averages can hide a poor experience for a significant minority of users. If your average latency is 100ms but your p99 is 5 seconds, 1% of your users are having a terrible experience.
*   **It reflects real user experience:** Focusing on p99 helps ensure that nearly all users have a satisfactory experience.

### 2.3. Alerting Engine

This is the brain of the system, responsible for evaluating your defined rules against the stored metrics.

*   **Prometheus Alertmanager:** Works with Prometheus to route alerts based on severity and grouping rules.
*   **Grafana Alerting:** Allows setting up alerts directly from Grafana dashboards, integrating with various data sources.
*   **Cloud-Native Alarms:** AWS CloudWatch Alarms, Google Cloud Monitoring Alert Policies, Azure Monitor Alert Rules.
*   **Commercial APM Monitor Definitions:** Datadog Monitors, New Relic Alerts.

**Alert Rule Examples:**

Let's assume we're using Prometheus and PromQL for our metrics.

**P99 Latency Alert:**
This rule fires if the 99th percentile of API request duration (in seconds) over the last 5 minutes exceeds 0.5 seconds (500ms).

yaml
ALERT CriticalAPILatencyHigh
  IF histogram_quantile(0.99, rate(api_request_duration_seconds_bucket[5m])) > 0.5
  FOR 2m # Sustain for at least 2 minutes to avoid flapping
  LABELS {
    severity="critical",
    priority="high"
  }
  ANNOTATIONS {
    summary="Critical API p99 latency is too high",
    description="The p99 latency for {{ $labels.api_path }} has exceeded 500ms for over 2 minutes. Current value: {{ $value | humanizeDuration }}",
    runbook="https://your-company.com/runbooks/api_latency.md"
  }


**Error Rate Alert:**
This rule fires if the ratio of 5xx errors to total requests over the last 5 minutes exceeds 1%.

yaml
ALERT CriticalAPIErrorRateHigh
  IF (sum(rate(api_requests_total{status=~"5..", api_path="critical_api"}[5m]))
      /
      sum(rate(api_requests_total{api_path="critical_api"}[5m]))) * 100 > 1
  FOR 1m # Sustain for at least 1 minute
  LABELS {
    severity="critical",
    priority="high"
  }
  ANNOTATIONS {
    summary="Critical API error rate is too high",
    description="The error rate for {{ $labels.api_path }} has exceeded 1% for over 1 minute. Current value: {{ $value | humanizePercentage }}",
    runbook="https://your-company.com/runbooks/api_error_rate.md"
  }


> **Pro Tip:** Use `FOR` clauses in your alert rules to prevent "flapping" (alerts rapidly firing and resolving). Requiring a condition to be true for a sustained period (e.g., 1-5 minutes) ensures that transient spikes don't trigger unnecessary notifications. Also, ensure your alert descriptions are rich, linking to runbooks or dashboards for quick incident resolution.

### 2.4. Notification Channels

Once an alert fires, it needs to reach the on-call engineer.

*   **PagerDuty / Opsgenie:** These are industry-standard tools for on-call schedule management, escalation policies, and reliable notification (SMS, phone calls, push notifications). They integrate with almost all alerting engines.
*   **Slack / Microsoft Teams:** Useful for team visibility and initial triage, but generally not sufficient for critical alerts that require guaranteed delivery.
*   **Email / SMS:** Basic options, often used as fallback or for lower-priority alerts.

### 2.5. On-Call Schedule Management

For a critical API, you need a clear rotation of engineers responsible for responding to alerts. Tools like PagerDuty and Opsgenie manage these schedules, escalation paths, and provide incident tracking.

## 3. Comparison / Trade-offs

Choosing the right components for your alerting system often involves trade-offs between cost, complexity, flexibility, and operational overhead. Here's a comparison of common approaches:

| Feature / System Type | Cloud-Native Managed Services (e.g., AWS, GCP) | Open-Source Stack (e.g., Prometheus + Grafana) | Commercial APM Tools (e.g., Datadog, New Relic) |
| :-------------------- | :--------------------------------------------- | :---------------------------------------------- | :---------------------------------------------- |
| **Setup Complexity**  | Low-Medium (configuration within cloud console) | High (requires infrastructure setup & maintenance) | Low (install agent, minimal configuration)      |
| **Cost**              | Pay-as-you-go, scales with usage; can be high at scale | Low (mainly infrastructure costs); high operational overhead | High (subscription-based, often per host/GB)    |
| **Scalability**       | Excellent (fully managed, auto-scaling)        | Manual scaling, complex to manage at very large scale | Excellent (fully managed by vendor)             |
| **Customization**     | Moderate (predefined metrics & alarm types)    | High (flexible metrics, PromQL, custom exporters) | Moderate-High (rich dashboards, custom metrics) |
| **Integration**       | Excellent within its specific cloud ecosystem  | Good (many exporters, Alertmanager integrations) | Excellent (rich plugin ecosystem, many integrations) |
| **Maintenance**       | Low (vendor handles underlying infrastructure) | High (self-managed updates, patching, scaling)  | Low (vendor handles platform maintenance)       |
| **Feature Set**       | Basic-Advanced (monitoring, logging, tracing, limited APM) | Advanced (powerful time-series querying, flexible alerting) | Comprehensive (APM, RUM, logging, security, synthetics) |

For a critical API, the choice often comes down to budget, existing cloud infrastructure, and the desire for full control versus managed convenience.

## 4. Real-World Use Case

Every major technology company that operates at scale and depends on the reliability of its APIs employs sophisticated alerting systems. Think of companies like **Netflix**, **Uber**, **Amazon**, **Google**, or **Stripe**.

*   **Netflix:** With thousands of microservices handling petabytes of data and millions of requests per second, Netflix relies heavily on detailed monitoring and intelligent alerting. If the p99 latency for their streaming API or error rates for their recommendation engine spike, on-call engineers are immediately notified. The "Why?" is simple: a delay of even a few hundred milliseconds can cause users to abandon their session, leading to direct business impact and user dissatisfaction.
*   **Uber:** For a ride-sharing platform, API latency is critical. A delay in matching riders to drivers, updating map locations, or processing payments can lead to missed rides, frustrated customers, and significant financial losses. Uber's systems continuously monitor the health of their microservices, including latency and error rates for critical APIs like `request_ride` or `update_driver_location`. Alerts ensure that operational teams can react instantly to prevent cascading failures.

The "Why" behind these robust alerting systems boils down to:

1.  **Maintaining SLOs/SLAs:** Ensuring that agreed-upon performance and reliability targets are met for internal and external customers.
2.  **Customer Satisfaction:** Fast, reliable services keep users happy and engaged.
3.  **Revenue Protection:** Downtime or degraded performance directly impacts sales, subscriptions, and transactions.
4.  **Proactive Problem Resolution:** Detecting issues early allows engineers to address them before they escalate into widespread outages, minimizing mean time to recovery (MTTR).
5.  **Operational Efficiency:** Automated alerting reduces the need for constant manual checks, freeing up engineers for more complex problem-solving and development.

By carefully designing and implementing an alerting system with appropriate metrics, thresholds, and notification strategies, you empower your engineering teams to maintain high service quality, even for the most critical of APIs.