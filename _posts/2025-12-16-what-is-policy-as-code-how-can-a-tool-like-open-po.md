---
title: "What is Policy as Code? How can a tool like Open Policy Agent (OPA) be used to enforce custom policies in your Kubernetes cluster (e.g., 'all images must come from a trusted registry')?"
date: 2025-12-16
categories: [System Design, Concepts]
tags: [interview, architecture, learning, security, kubernetes, policy-as-code, opa, rego]
toc: true
layout: post
---

## 1. The Core Concept

Imagine trying to build a new district in a city without any zoning laws, building codes, or environmental regulations. Each developer would construct whatever they wanted, leading to chaos, safety hazards, and an unsustainable environment. **Policy as Code** brings the same discipline, automation, and version control to your infrastructure and applications that you've come to expect from your application code.

It's about defining rules, guidelines, and constraints for your systems in a machine-readable, declarative format that can be version-controlled, tested, and deployed like any other piece of code. This allows for consistent, automated, and auditable enforcement of your organization's security, compliance, and operational best practices.

> **Pro Tip: Definition of Policy as Code**
> **Policy as Code (PaC)** is the practice of defining, managing, and enforcing policies through code, typically stored in a version control system. This approach enables automation, consistency, and audibility across various technical domains, including infrastructure, security, and application deployment.

## 2. Deep Dive & Architecture

**Open Policy Agent (OPA)** is a cloud-native, general-purpose policy engine that provides a unified way to enforce policies across the entire stack. Whether it's microservices, Kubernetes, CI/CD pipelines, API gateways, or SSH, OPA can decouple policy enforcement from application logic.

At its core, OPA evaluates policy decisions based on structured data (JSON) input and policies written in its purpose-built language, **Rego**. When an application needs to make a policy decision, it queries OPA, providing relevant data as input. OPA then processes this input against its configured policies and returns a decision (e.g., "allow" or "deny").

### OPA's Role in Kubernetes

In a Kubernetes cluster, OPA commonly operates as an **Admission Controller**. This allows OPA to intercept requests to the Kubernetes API server *before* objects are persisted to `etcd`. There are two main types of admission controllers OPA can act as:

1.  **Validating Admission Controller:** OPA validates whether a request conforms to defined policies. If the policy returns "deny," the request is rejected.
2.  **Mutating Admission Controller:** OPA can modify incoming requests before they are validated or persisted (e.g., adding default labels, injecting sidecars).

### Example: Enforcing Trusted Image Registries with OPA and Kubernetes

Let's consider the policy: "all images must come from a trusted registry."

1.  **The Request:** A user or CI/CD pipeline sends a `kubectl apply` command to create a Deployment in Kubernetes.
2.  **API Server Interception:** The Kubernetes API server receives the request.
3.  **Admission Controller Webhook:** The API server, configured with an OPA webhook, sends the incoming Deployment request (as JSON) to OPA.
4.  **OPA Policy Evaluation:** OPA receives the JSON request. It evaluates this input against its loaded Rego policies.
5.  **Policy Decision:**
    *   If the image source (e.g., `my-internal-registry.com/my-app:latest`) matches the trusted registry pattern defined in Rego, OPA returns an "allow" decision.
    *   If the image source (e.g., `docker.io/evil-app:latest`) does *not* match, OPA returns a "deny" decision, optionally with a detailed explanation.
6.  **Kubernetes Action:**
    *   "Allow": The API server continues processing the request, and the Deployment is created.
    *   "Deny": The API server rejects the request, informing the user why the Deployment could not be created.

### A Glimpse of Rego Policy for Trusted Images:

rego
package kubernetes.trusted_images

import data.kubernetes.trusted_registries

deny[msg] {
    some i
    # Check if a container image exists in the deployment spec
    input.request.kind.kind == "Pod"
    image := input.request.object.spec.containers[i].image

    # Check if the image starts with any of the trusted registry prefixes
    not starts_with_trusted_registry(image, trusted_registries.allow_list)

    msg := sprintf("Image '%v' is not from a trusted registry. Allowed registries are: %v", [image, trusted_registries.allow_list])
}

# Helper function to check if an image starts with any trusted registry prefix
starts_with_trusted_registry(image, allow_list) {
    some i
    registry_prefix := allow_list[i]
    startswith(image, registry_prefix)
}

# Define our trusted registries (this could come from a ConfigMap)
trusted_registries := {
    "allow_list": [
        "my-internal-registry.com/",
        "gcr.io/my-project/",
        "quay.io/my-org/"
    ]
}


This Rego policy snippet demonstrates how to define a list of allowed registries and then check if any container image within a Pod specification originates from one of these trusted sources.

## 3. Comparison / Trade-offs

Implementing policy enforcement using **Policy as Code** with tools like OPA offers significant advantages over traditional, imperative approaches where policy logic might be hardcoded into applications or scripts.

| Feature / Aspect       | Traditional Imperative Enforcement                               | Policy as Code (OPA)                                                                 |
| :--------------------- | :--------------------------------------------------------------- | :----------------------------------------------------------------------------------- |
| **Definition**         | Policy logic embedded within application code, scripts, or firewall rules. | Policies defined declaratively in a high-level language (e.g., Rego).                 |
| **Management**         | Scattered across various systems, often manual and inconsistent. | Centralized, version-controlled (GitOps), and auditable.                             |
| **Consistency**        | Prone to inconsistencies as policies are re-implemented in different places. | Highly consistent; a single policy engine enforces rules uniformly across the stack.  |
| **Auditing**           | Difficult to track changes, compliance checks are often manual.    | Full audit trail via Git history; automated compliance reporting.                     |
| **Flexibility**        | Changes require code modifications, recompilation, or script updates. | Policies can be updated and deployed independently of applications, hot-reloaded.     |
| **Testability**        | Unit testing policy logic can be complex and intertwined with application logic. | Policies are declarative and easy to unit test in isolation using OPA's tooling.      |
| **Scalability**        | Enforcement scales with each application instance; can lead to N+1 problem. | OPA instances can be deployed and scaled independently, serving multiple clients.     |
| **Security**           | Risk of policy logic being bypassed or having security vulnerabilities in custom implementations. | Decoupled policy engine reduces attack surface; policies are transparent and auditable. |
| **Complexity**         | Can become complex to maintain as policy requirements grow and evolve across many services. | Introduces a new language (Rego) but simplifies overall policy governance.             |

## 4. Real-World Use Case

The "all images must come from a trusted registry" policy is a crucial **supply chain security** control. Many leading organizations leverage OPA for this very reason, alongside other policies, to secure their Kubernetes clusters and enforce compliance.

**Why is this so important?**

*   **Security:** Prevents developers from accidentally or maliciously deploying images from unknown or untrusted sources, which could contain vulnerabilities, malware, or backdoors. This is a critical step in preventing software supply chain attacks.
*   **Compliance:** Many industry regulations (e.g., SOC 2, PCI DSS, HIPAA) require strict control over what software runs in production environments. Policy as Code provides an auditable, automated mechanism to prove compliance.
*   **Operational Consistency:** Ensures that all deployments adhere to organizational standards, reducing configuration drift and simplifying troubleshooting.
*   **Shift Left Security:** By enforcing policies at the admission controller level, issues are caught early in the development lifecycle, preventing non-compliant workloads from even reaching the cluster. This is significantly cheaper and faster than discovering problems in production.

Beyond trusted registries, OPA is widely used in Kubernetes for:

*   **Resource Limits:** Ensuring all pods have CPU/memory requests and limits.
*   **Network Policies:** Defining required network segmentation.
*   **Labeling and Annotation Conventions:** Enforcing metadata standards for better management.
*   **Role-Based Access Control (RBAC) Augmentation:** Adding fine-grained authorization beyond native Kubernetes RBAC.
*   **Security Best Practices:** Disallowing privileged containers, enforcing read-only root filesystems, and requiring specific security contexts.

By embracing **Policy as Code** with tools like OPA, organizations can automate governance, enhance security posture, and achieve continuous compliance across their cloud-native environments.