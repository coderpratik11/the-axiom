---
title: "What is BGP hijacking? At a high level, explain how an attacker can illegitimately reroute internet traffic by announcing IP prefixes they do not own."
date: 2025-12-16
categories: [System Design, Networking]
tags: [interview, architecture, learning, bgp, security, networking]
toc: true
layout: post
---

Navigating the internet feels seamless, but beneath the surface lies a complex web of interconnected networks, all orchestrated by a critical protocol: the Border Gateway Protocol (BGP). While indispensable for global connectivity, BGP's inherent trust model also presents a significant vulnerability: **BGP hijacking**. This article will demystify BGP hijacking, explaining how an attacker can illicitly reroute internet traffic.

## 1. The Core Concept

Imagine the internet as a vast postal service. Each country or region has its own postal network (an **Autonomous System**), and within that network, it handles mail for specific zip codes ( **IP prefixes**). When you send a letter, the postal service consults a global routing table to find the most efficient path to the destination zip code.

> **BGP Hijacking Definition:** BGP hijacking is the illegitimate takeover of groups of IP addresses (IP prefixes) by an unauthorized Autonomous System (AS). This is achieved by announcing to the internet's routing tables that the attacker's AS is the correct path for traffic destined for those IP prefixes, even though they do not legitimately own or control them.

In our postal analogy, a BGP hijack is like a rogue post office suddenly announcing to the entire global postal system that it can deliver mail for zip codes belonging to another, legitimate post office. Consequently, mail intended for the rightful recipient gets rerouted to the rogue post office, which can then read, modify, or discard it before potentially forwarding it on, or simply dropping it.

## 2. Deep Dive & Architecture

At its heart, BGP is the **routing protocol of the internet**. It enables different **Autonomous Systems (ASes)** to exchange routing information. An AS is a collection of IP networks and routers under the control of a single entity (e.g., an ISP, a large corporation, a university). Each AS has a unique identifier called an **Autonomous System Number (ASN)**, like `AS64496`.

Here's how it generally works and where the vulnerability lies:

*   **IP Prefixes:** Blocks of IP addresses are grouped into prefixes (e.g., `192.0.2.0/24`), which an AS "owns" or has legitimate permission to route traffic for.
*   **BGP Peering:** ASes establish BGP peering sessions with their neighbors to exchange routing information. They announce which IP prefixes they can reach and the "path" (sequence of ASes) traffic would traverse to get there.
*   **Path Vector Protocol:** BGP is a **path vector protocol**. When an AS receives a route announcement, it adds its own ASN to the AS path and re-announces it to its neighbors. Routers decide the "best" path based on various attributes, with a key one being the **shortest AS path**.
*   **The Trust Model:** BGP operates on a largely **trust-based model**. When an AS announces a route, other ASes generally assume the announcement is legitimate. There isn't robust built-in cryptographic verification of ownership for every prefix announcement.

### How an Attacker Hijacks Traffic:

An attacker, controlling an AS, can initiate a BGP hijack in a few primary ways:

1.  **Unauthorized Prefix Announcement:** The attacker's AS simply announces an **IP prefix** that it does not legitimately own. If this announcement reaches neighboring ASes, they might update their routing tables to send traffic for that prefix to the attacker's AS.
    
    Legitimate AS (AS65000) owns: 203.0.113.0/24
    Attacker AS (AS65535) announces: 203.0.113.0/24
    
    Traffic intended for `203.0.113.0/24` might now flow to `AS65535`.

2.  **More Specific Prefix Announcement:** Even more insidious, an attacker can announce a **more specific IP prefix** (a smaller block of addresses) that is contained within a legitimate, larger prefix. Because routing protocols generally prefer more specific routes, this announcement can "override" the legitimate, broader announcement.
    
    Legitimate AS (AS65000) owns: 203.0.113.0/24
    Attacker AS (AS65535) announces: 203.0.113.128/25
    
    Traffic for the `203.0.113.128/25` portion of the legitimate prefix will be diverted to `AS65535`. This is a common and effective hijacking method.

3.  **AS Path Falsification:** An attacker might try to make their announced path look "better" (e.g., shorter) by manipulating the AS path attribute, although this is less common and harder to sustain than prefix announcements.

Once traffic is rerouted to the attacker's AS, they can:
*   **Eavesdrop:** Inspect sensitive data.
*   **Blackhole:** Drop the traffic, causing a denial of service.
*   **Man-in-the-Middle:** Modify traffic before forwarding it to the legitimate destination, allowing for data alteration or credential theft.

> **Pro Tip:** Understanding AS path selection is crucial. BGP has a complex decision process, but generally, the shortest AS path is preferred. If an attacker can announce a route that appears to have a shorter path to a destination than the legitimate route, they can attract traffic.

## 3. Comparison: Accidental Misconfiguration vs. Malicious Hijack

While we focus on malicious attacks, it's important to recognize that many BGP "hijacks" in the real world are the result of accidental misconfigurations. Both can have similar disruptive effects.

| Feature             | Accidental BGP Misconfiguration                  | Malicious BGP Hijack                             |
| :------------------ | :----------------------------------------------- | :----------------------------------------------- |
| **Intent**          | Unintentional error by an AS administrator.       | Deliberate action by an attacker for illicit gain. |
| **Origin**          | Legitimate AS mistakenly announces wrong prefix or propagates incorrect routes. | Rogue AS announces prefixes it doesn't own.      |
| **Duration**        | Often quickly detected and resolved once identified. | Can be sustained and hidden for longer periods, potentially using "leak-and-return" to avoid detection. |
| **Detection**       | Can be challenging, often identified by downstream ISPs or monitoring services due to reachability issues. | Similar detection methods, but often involves monitoring for suspicious new prefix announcements. |
| **Impact**          | Network outages, traffic blackholing, routing loops, denial of service. | Data interception, censorship, DDoS attacks, cryptocurrency theft, financial fraud. |
| **Motivation**      | Human error, lack of proper validation.          | Financial gain, espionage, political activism, sabotage. |
| **Mitigation**      | Rigorous internal configuration validation, RPKI adoption, BGP monitoring. | RPKI adoption, BGP monitoring, BGP filtering, peer coordination. |

## 4. Real-World Implications and Use Cases

BGP hijacking is not just a theoretical threat; it has manifested in numerous high-profile incidents, demonstrating its profound impact on internet stability and security. These incidents highlight why safeguarding BGP is a paramount concern for internet service providers and large enterprises alike.

*   **The YouTube Blackout (2008):** One of the most famous incidents involved Pakistan Telecom attempting to block access to YouTube within Pakistan by announcing more specific routes for YouTube's IP prefixes. Due to BGP's path preference, these routes propagated globally, effectively making YouTube inaccessible worldwide for several hours. This demonstrated how a local censorship attempt could inadvertently cause global disruption.

*   **Cryptocurrency Theft (2018):** MyEtherWallet, a popular cryptocurrency wallet service, fell victim to a BGP hijack. Attackers rerouted traffic intended for MyEtherWallet's DNS provider, diverting users to a phishing site designed to steal cryptocurrency. This illustrates the direct financial implications of such attacks.

*   **Amazon S3 and Cloudflare (2019):** A small ISP in Pennsylvania mistakenly announced routes for IP prefixes belonging to Amazon and Cloudflare. This accidental misconfiguration caused traffic for parts of Amazon's services (like S3) and Cloudflare's network to be misrouted, leading to widespread outages for various websites and services. While accidental, the impact was indistinguishable from a malicious attack initially.

### Why It Matters:

1.  **Security Risk:** Hijacks can be used for Man-in-the-Middle attacks, allowing attackers to intercept, inspect, and modify traffic, compromising sensitive data like login credentials, financial transactions, or corporate secrets.
2.  **Censorship and Surveillance:** Governments or malicious actors can reroute traffic to "blackhole" destinations (effectively blocking access) or through surveillance equipment.
3.  **Denial of Service (DoS):** By attracting traffic and then dropping it, attackers can launch distributed denial-of-service (DDoS) attacks against targeted services, rendering them unreachable.
4.  **Financial Impact:** Disrupted services, stolen data, and lost business can lead to significant financial losses for organizations and individuals.

Protecting against BGP hijacking requires a collaborative effort across the internet community, primarily through widespread adoption of technologies like **RPKI (Resource Public Key Infrastructure)**, which cryptographically validates the ownership of IP prefixes, and robust BGP monitoring tools. As long as BGP remains the internet's core routing mechanism, understanding and mitigating its vulnerabilities will remain a critical task for network architects and security professionals.