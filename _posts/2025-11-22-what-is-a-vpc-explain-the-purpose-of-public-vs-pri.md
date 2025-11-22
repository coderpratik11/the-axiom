---
title: "What is a VPC? Explain the purpose of public vs. private subnets in designing a secure cloud network architecture."
date: 2025-11-22
categories: [System Design, Cloud Networking]
tags: [vpc, aws, azure, gcp, cloud, networking, security, architecture, subnets]
toc: true
layout: post
---

## 1. The Core Concept

Imagine you're moving into a vast, shared office building – that's the cloud. While you share the building with many other companies, you wouldn't want your confidential meetings or sensitive documents visible to everyone. Instead, you'd want your own dedicated, secure office space with locked doors, controlled access, and your own internal network.

This secure, isolated space in the cloud is precisely what a **Virtual Private Cloud (VPC)** provides.

> A **Virtual Private Cloud (VPC)** is a logically isolated section of a cloud provider's network where you can launch resources in a virtual network that you define. It grants you complete control over your virtual networking environment, including selection of your own IP address range, creation of subnets, and configuration of route tables and network gateways.

In simpler terms, a VPC is your own private segment of the internet within a public cloud, completely isolated from other customers' VPCs. It gives you the power to sculpt your network topology, defining boundaries and access rules just as you would in a traditional on-premises data center. This isolation is fundamental for security, compliance, and architectural flexibility.

## 2. Deep Dive & Architecture

Within your VPC, you don't just have one big, flat network. You further subdivide it into smaller, manageable segments called **subnets**. These subnets are crucial for organizing your resources and, more importantly, implementing robust security postures.

### 2.1 Subnets: The Building Blocks

A **subnet** is a range of IP addresses in your VPC. When you launch instances or services, you deploy them into specific subnets. The primary distinction between subnets lies in their connectivity to the public internet:

#### Public Subnets
A **public subnet** is a subnet whose traffic is routed to an **Internet Gateway (IGW)**. An IGW is a horizontally scaled, redundant, and highly available VPC component that allows communication between instances in your VPC and the internet.

*   **Internet Access**: Instances in a public subnet can send and receive traffic directly from the internet. They typically have **public IP addresses** (or are associated with Elastic IPs) that are directly reachable from the internet.
*   **Use Cases**: This is where you place resources that absolutely *need* to be directly accessible from the internet. Examples include:
    *   **Load Balancers**: To distribute incoming traffic to your application servers.
    *   **Web Servers (Front-end)**: That serve public web pages or APIs.
    *   **Jump Boxes/Bastion Hosts**: Secure servers used to connect to instances in private subnets.
*   **Security**: While they offer internet connectivity, public subnets are protected by **Network Access Control Lists (NACLs)** and **Security Groups**. It's critical to configure these tightly to allow only necessary inbound traffic.

#### Private Subnets
A **private subnet** is a subnet whose traffic is *not* routed to an Internet Gateway. Instances in a private subnet cannot directly send or receive traffic from the internet.

*   **Internet Access**: They cannot directly communicate with the internet. However, they can initiate outbound connections to the internet via a **NAT Gateway** (or NAT instance) located in a public subnet. This allows private instances to fetch software updates or connect to external APIs without exposing them to unsolicited inbound connections.
*   **Use Cases**: This is where you place your most sensitive resources that should *never* be directly exposed to the internet. Examples include:
    *   **Database Servers**: Storing sensitive customer data.
    *   **Application Servers (Back-end)**: Processing business logic.
    *   **Cache Servers**: Like Redis or Memcached.
    *   **Internal Microservices**: That only communicate with other services within your VPC.
*   **Security**: Inherently more secure due to the lack of direct internet exposure. All inbound traffic must pass through other layers (like a load balancer in a public subnet or a VPN connection).

### 2.2 Network Flow & Routing

Every VPC has one or more **route tables**. A route table contains a set of rules, called routes, that determine where network traffic from your subnet is directed.

*   For a public subnet, the route table will have a route pointing `0.0.0.0/0` (all traffic) to the Internet Gateway.
*   For a private subnet, the route table will have a route pointing `0.0.0.0/0` to a NAT Gateway (for outbound internet access) or may not have an internet route at all.


# Example VPC CIDR: 10.0.0.0/16

# Public Subnet (e.g., 10.0.1.0/24)
# Route Table for Public Subnet:
# Destination      | Target
# -----------------|--------------------
# 10.0.0.0/16      | local (within VPC)
# 0.0.0.0/0        | igw-xxxxxxxxxxxxxxx (Internet Gateway)

# Private Subnet (e.g., 10.0.2.0/24)
# Route Table for Private Subnet:
# Destination      | Target
# -----------------|--------------------
# 10.0.0.0/16      | local (within VPC)
# 0.0.0.0/0        | nat-xxxxxxxxxxxxxxx (NAT Gateway in Public Subnet)


> **Pro Tip: NACLs vs. Security Groups**
>
> *   **Network Access Control Lists (NACLs)** operate at the **subnet level**. They are stateless, meaning inbound and outbound rules are evaluated independently. They act as firewalls for subnets.
> *   **Security Groups (SGs)** operate at the **instance level**. They are stateful, meaning if you allow an inbound request, the outbound response is automatically allowed. They act as firewalls for individual instances.
>
> Use NACLs for broad, deny-all rules at the subnet boundary and Security Groups for granular, instance-specific allow rules.

## 3. Comparison / Trade-offs

Here's a direct comparison between public and private subnets:

| Feature           | Public Subnet                                    | Private Subnet                                       |
| :---------------- | :----------------------------------------------- | :--------------------------------------------------- |
| **Internet Access** | Direct inbound and outbound via Internet Gateway | No direct inbound from internet; outbound via NAT Gateway (optional) |
| **IP Addressing** | Requires public IP address (or Elastic IP)       | Only uses private IP addresses                       |
| **Primary Use Cases** | Load balancers, web servers, jump boxes, public-facing APIs | Database servers, application servers, internal services, caches |
| **Security Posture** | Exposed to internet, requires stringent Security Group/NACL rules | Inherently more secure due to isolation from direct internet access |
| **Key Components** | Internet Gateway, Route Table                    | NAT Gateway (for outbound internet), Route Table       |
| **Example Resources** | AWS ELB/ALB, EC2 (web tier)                      | AWS RDS, EC2 (app tier), ElastiCache                 |

> **Security Warning:** Never place sensitive data stores (like databases) in a public subnet. It's a fundamental security flaw that dramatically increases your attack surface.

## 4. Real-World Use Case

Let's illustrate with a common **three-tier web application architecture**, which is a quintessential example of secure cloud networking design using public and private subnets.

### The Architecture:

1.  **Presentation Tier (Public Subnet):**
    *   **Load Balancer (e.g., AWS ALB/ELB):** Sits in a public subnet. It receives all incoming HTTP/HTTPS requests from the internet. Its primary job is to distribute these requests to the application servers in the private subnets.
    *   **Why a Public Subnet?** The load balancer is the public entry point for your application. It *must* be internet-facing to receive user requests.

2.  **Application Tier (Private Subnet 1):**
    *   **Application Servers (e.g., EC2 instances, containers):** These instances host your application logic. They are placed in a private subnet.
    *   **NAT Gateway:** Resides in the public subnet and allows application servers in the private subnet to initiate outbound internet connections (e.g., to download updates, connect to third-party APIs) without being directly accessible from the internet.
    *   **Why a Private Subnet?** Your application servers don't need direct inbound internet access. All legitimate traffic comes *from* the load balancer. By placing them in a private subnet, you reduce their exposure to direct attacks. They can still fetch necessary external resources via the NAT Gateway.

3.  **Data Tier (Private Subnet 2):**
    *   **Database Servers (e.g., AWS RDS, self-managed databases):** This is where your critical data resides. These servers are placed in their own, even more isolated, private subnet.
    *   **Why a Private Subnet?** Databases hold the most sensitive information and should *never* be directly exposed to the internet. They only communicate with the application servers in the private application tier. This layered approach creates multiple barriers for potential attackers.

### The "Why":

This design achieves several critical goals:

*   **Enhanced Security:** By separating public-facing components from internal application and data components, you minimize the attack surface. An attacker would first need to compromise the load balancer, then the application servers, before potentially reaching the database. Each tier acts as a defense layer.
*   **Isolation of Sensitive Data:** Your databases, containing customer information or business logic, are completely shielded from direct internet access.
*   **Scalability & Availability:** Each tier can be scaled independently, and placing resources across multiple subnets (often in different availability zones) improves fault tolerance.
*   **Compliance:** Many regulatory standards (like PCI DSS, HIPAA) require strict network segmentation and isolation of sensitive data, which this architecture inherently provides.

By diligently segmenting your cloud network with public and private subnets, you lay the foundation for a secure, scalable, and resilient cloud architecture. It's a fundamental concept for any Principal Software Engineer working in the cloud.