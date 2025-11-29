---
title: "What is the difference between a Security Group and a Network Access Control List (NACL) in AWS? Which one is stateful and which is stateless?"
date: 2025-11-29
categories: [System Design, AWS Networking]
tags: [aws, securitygroup, nacl, networking, security, interview, architecture, learning]
toc: true
layout: post
---

As a Principal Software Engineer, a deep understanding of AWS networking and security primitives is fundamental to building robust and secure cloud architectures. Among the most frequently confused, yet critical, components are **Security Groups** and **Network Access Control Lists (NACLs)**. While both serve as virtual firewalls in AWS, they operate at different layers, offering distinct functionalities that are crucial for a layered security approach.

Let's demystify these core AWS services.

## 1. The Core Concept

Imagine you're securing a building. You'd likely have multiple layers of defense: an outer perimeter fence and individual security for specific rooms or entrances. This analogy helps us understand the roles of NACLs and Security Groups in AWS.

> **Security Group (SG): Your Front Door Bouncer (Stateful)**
> A **Security Group** acts as a virtual firewall for your EC2 instances (or other network interfaces). It controls inbound and outbound traffic *at the instance level*. Think of it as a bouncer at the door of a specific room. This bouncer is smart: if he lets you out, he automatically knows to let you back in when you return.

> **Network Access Control List (NACL): Your Perimeter Fence Guard (Stateless)**
> A **Network Access Control List (NACL)** acts as a virtual firewall for your subnets. It controls inbound and outbound traffic *at the subnet level*. Envision a guard at the perimeter fence of your property. This guard isn't very smart; for every single person trying to enter or exit, he strictly checks a list and needs explicit instructions for both directions of travel, every single time. He doesn't remember past interactions.

## 2. Deep Dive & Architecture

### Security Groups

Security Groups are the most common and often the first line of defense for your AWS resources.

*   **Scope**: Operates at the **instance or Elastic Network Interface (ENI) level**. This means rules apply directly to individual EC2 instances, RDS instances, Load Balancers, etc.
*   **Statefulness**: **Stateful**. If you allow outbound traffic for a specific port (e.g., 443 HTTPS), the Security Group automatically allows the inbound response traffic for that connection, regardless of inbound rules. Conversely, if you allow inbound traffic, the outbound response is automatically allowed.
*   **Rules**:
    *   Only **allow rules** are supported. You cannot explicitly deny traffic with a Security Group.
    *   Rules are evaluated for all traffic; there's no concept of rule precedence based on order.
    *   You can reference other Security Groups in your rules, which is incredibly powerful for inter-service communication (e.g., "allow inbound HTTP from instances associated with the 'Web-Servers-SG'").
*   **Default Behavior**: By default, a Security Group allows all outbound traffic and denies all inbound traffic.
*   **Association**: An instance can be associated with multiple Security Groups, and a Security Group can be associated with multiple instances.

#### Example Security Group Rules (Conceptual)

json
{
  "GroupName": "Web-Server-SG",
  "Description": "Allows HTTP/HTTPS inbound, all outbound",
  "Ingress": [
    {
      "IpProtocol": "tcp",
      "FromPort": 80,
      "ToPort": 80,
      "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
      "Description": "Allow HTTP from anywhere"
    },
    {
      "IpProtocol": "tcp",
      "FromPort": 443,
      "ToPort": 443,
      "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
      "Description": "Allow HTTPS from anywhere"
    }
  ],
  "Egress": [
    {
      "IpProtocol": "-1", // All protocols
      "FromPort": 0,
      "ToPort": 0,
      "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
      "Description": "Allow all outbound traffic"
    }
  ]
}

*Note: In the AWS Console or CLI, you typically add rules one by one, rather than defining a full JSON blob like this.*

### Network Access Control Lists (NACLs)

NACLs provide a crucial, coarser-grained layer of network security.

*   **Scope**: Operates at the **subnet level**. Rules apply to *all* instances within the associated subnet.
*   **Statefulness**: **Stateless**. Inbound and outbound traffic are evaluated completely independently. If you allow inbound traffic on port 80, you *must* also explicitly allow the outbound response traffic on the appropriate ephemeral ports (typically `1024-65535`) for the connection to be successful.
*   **Rules**:
    *   Supports both **allow and deny rules**. This is a key differentiator, allowing you to explicitly block malicious IPs or ranges.
    *   Rules are numbered and evaluated in **order of precedence** from lowest to highest. Once a rule is matched, it is applied, and no further rules are evaluated for that traffic.
    *   Each NACL has an implicit `deny all` rule at the highest number (e.g., `*` or `32767`).
*   **Default Behavior**:
    *   A **default NACL** (created with your VPC) allows all inbound and outbound traffic.
    *   **Custom NACLs** (created by you) explicitly deny all inbound and outbound traffic until rules are added.
*   **Association**: A subnet can be associated with only one NACL, but a NACL can be associated with multiple subnets.

#### Example NACL Rules (Conceptual)


// Inbound Rules for a Public Subnet:
Rule # | Type    | Protocol | Port Range        | Source       | Allow/Deny
-------------------------------------------------------------------------------
100    | HTTP    | TCP      | 80                | 0.0.0.0/0    | ALLOW
110    | HTTPS   | TCP      | 443               | 0.0.0.0/0    | ALLOW
120    | SSH     | TCP      | 22                | 192.168.1.0/24 | ALLOW (e.g., management subnet)
*      | ALL     | ALL      | ALL               | 0.0.0.0/0    | DENY (Implicit)

// Outbound Rules for the same Public Subnet:
Rule # | Type    | Protocol | Port Range        | Destination  | Allow/Deny
-------------------------------------------------------------------------------
100    | ALL     | TCP      | 1024-65535        | 0.0.0.0/0    | ALLOW (for ephemeral ports for responses)
110    | HTTPS   | TCP      | 443               | 0.0.0.0/0    | ALLOW (e.g., for external API calls)
*      | ALL     | ALL      | ALL               | 0.0.0.0/0    | DENY (Implicit)


> **Pro Tip:** When setting up stateless NACL rules, always remember the ephemeral port range (`1024-65535`). For an inbound connection on a well-known port (e.g., 80, 443, 22), the outbound response will use a port from this ephemeral range. If you don't explicitly allow outbound traffic on these ports, the connection will fail.

## 3. Comparison / Trade-offs

The distinct characteristics of Security Groups and NACLs make them suitable for different use cases and layers of defense.

| Feature             | Security Group (SG)                            | Network Access Control List (NACL)             |
| :------------------ | :--------------------------------------------- | :--------------------------------------------- |
| **Scope**           | Instance/ENI level                             | Subnet level                                   |
| **Statefulness**    | **Stateful** (return traffic automatically allowed) | **Stateless** (inbound and outbound rules evaluated independently) |
| **Rule Type**       | Allow rules only                               | Allow and Deny rules                           |
| **Rule Evaluation** | All rules evaluated; no order of precedence    | Rules evaluated in number order (lowest to highest); first match wins |
| **Default Behavior**| All outbound allowed, all inbound denied       | Default NACL: All traffic allowed; Custom NACL: All traffic denied |
| **Target**          | Applied to individual instances/resources      | Applied to subnets (affects all instances in subnet) |
| **Granularity**     | Fine-grained control                           | Coarse-grained control                         |
| **Recommendation**  | Best practice to use for most instance-level security | Use as a secondary, overarching layer of defense for subnets |

> **Warning:** Be extremely cautious when modifying NACLs. Because they are stateless and apply to entire subnets, misconfigured NACLs can easily block all traffic to/from your instances within that subnet, leading to widespread outages. Always test changes thoroughly in non-production environments first.

## 4. Real-World Use Case

In a typical AWS architecture, you will almost always use **both** Security Groups and NACLs, implementing a strategy known as **defense-in-depth**.

Consider a classic three-tier web application:
1.  **Web Tier (Public Subnet):** Contains load balancers and web servers.
2.  **Application Tier (Private Subnet):** Contains application servers.
3.  **Database Tier (Private Subnet):** Contains database instances.

Here's how SG and NACLs would work together:

*   **NACL for Public Subnet (Web Tier):**
    *   **Inbound:** Allow HTTP (80), HTTPS (443) from `0.0.0.0/0` (internet). Allow SSH (22) from a trusted `management CIDR` (e.g., your office IP).
    *   **Outbound:** Allow ephemeral ports (`1024-65535`) to `0.0.0.0/0` (for web responses), to the Application Tier's subnet CIDR (for app requests).
    *   *Why?* This provides a coarse filter at the network perimeter, blocking any obvious unwanted traffic *before* it even reaches the instance.

*   **Security Group for Web Servers (Web Tier):**
    *   **Inbound:** Allow HTTP (80) and HTTPS (443) from the Load Balancer's Security Group (or `0.0.0.0/0` if directly exposed). Allow SSH (22) from a `Bastion Host's Security Group`.
    *   **Outbound:** Allow traffic to the Application Tier's Security Group (e.g., port 8080).
    *   *Why?* This fine-tunes access to the specific web server instances, ensuring only legitimate traffic for the web application and management can reach them. It doesn't care about the internet as a whole, just the traffic meant for *this specific web server*.

*   **NACL for Private Subnet (Application Tier):**
    *   **Inbound:** Allow traffic from the Web Tier's subnet CIDR on application ports (e.g., 8080). Allow SSH (22) from the trusted `management CIDR`.
    *   **Outbound:** Allow ephemeral ports to the Web Tier subnet (for responses) and to the Database Tier subnet CIDR on database ports.
    *   *Why?* Blocks any traffic from the internet or other untrusted sources from reaching the application tier.

*   **Security Group for Application Servers (Application Tier):**
    *   **Inbound:** Allow application ports (e.g., 8080) only from the `Web Server's Security Group`. Allow SSH (22) only from the `Bastion Host's Security Group`.
    *   **Outbound:** Allow database port (e.g., 3306) only to the `Database Server's Security Group`.
    *   *Why?* Ensures only authorized web servers can talk to application servers, and only authorized admins can SSH in.

*   **NACL for Private Subnet (Database Tier):**
    *   **Inbound:** Allow database ports (e.g., 3306) only from the Application Tier's subnet CIDR.
    *   **Outbound:** Allow ephemeral ports back to the Application Tier subnet.
    *   *Why?* Prevents *any* direct access to the database from the internet or other unauthorized subnets.

*   **Security Group for Database Servers (Database Tier):**
    *   **Inbound:** Allow database port (e.0. 3306) only from the `Application Server's Security Group`.
    *   *Why?* The most restrictive, ensuring only the application servers can access the database, enforcing the principle of least privilege.

By combining Security Groups and NACLs, you create a robust, multi-layered security posture. NACLs provide a broad stroke of network-level filtering, catching unwanted traffic at the subnet boundary, while Security Groups offer fine-grained, instance-level protection for your applications and services. Understanding their differences and leveraging their strengths is key to designing secure and resilient AWS environments.