---
title: "Design a system to prevent other websites from embedding your images or videos on their pages, which consumes your bandwidth."
date: 2025-12-21
categories: [System Design, Security]
tags: [hotlinking, system-design, security, bandwidth, cdn, referer, signed-urls]
toc: true
layout: post
---

Bandwidth isn't free. If your website hosts valuable images, videos, or other media, you might discover that other sites are directly linking to your assets, effectively stealing your bandwidth and increasing your operational costs. This practice, known as hotlinking, can significantly impact your infrastructure and budget. As a Principal Software Engineer, understanding how to mitigate this is a critical skill for building robust and cost-effective systems.

## 1. The Core Concept

Imagine you own a fantastic coffee shop that roasts its own beans. One day, you notice a competitor across the street is offering "your" coffee, but they're not buying it from you. Instead, they're simply pointing their customers to your shop to pick up their orders, effectively using your inventory, baristas, and space for their profit, all while you bear the costs.

> **Definition:** **Hotlinking** (or inline linking) occurs when a website embeds an image, video, or other media file from another website by directly linking to its URL. The asset remains hosted on the original server, consuming its bandwidth and resources, but appears as if it's part of the embedding website.

The primary motivation for preventing hotlinking is **cost control**. Every time someone views an embedded asset from your server on another site, it consumes your outgoing bandwidth. For high-traffic sites or those with many large media files, this can translate into substantial, unnecessary expenses. It also adds load to your servers and can sometimes even be a legal concern regarding intellectual property.

## 2. Deep Dive & Architecture

Preventing hotlinking typically involves instructing your web server or Content Delivery Network (CDN) to check certain HTTP headers or validate access tokens before serving a media file. The two most common and effective methods are checking the HTTP Referer header and using signed URLs.

### 2.1. Method 1: HTTP Referer Header Check

The **`Referer`** HTTP header (yes, it's misspelled in the specification, but that's how it is) is sent by a web browser to indicate the URL of the page that linked to the requested resource. By inspecting this header, your server can determine if the request for an image or video originates from your own domain or an approved list of domains.

**How it works:**
1.  A user visits `https://example.com`.
2.  `example.com` has an image `<img src="https://yourdomain.com/images/my-image.jpg">`.
3.  The browser sends a request to `https://yourdomain.com/images/my-image.jpg`.
4.  Crucially, this request includes the header: `Referer: https://example.com`.
5.  Your server (or CDN) receives this request, checks the `Referer` header, and if `example.com` is *not* `yourdomain.com` (or an allowed domain), it can deny the request.

**Implementation (Nginx Example):**

nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location ~* \.(jpg|jpeg|png|gif|webp|mp4|webm|ogg)$ {
        # Allow requests with no Referer, from your own domain, or specified trusted domains
        valid_referers none blocked server_names *.yourdomain.com yourdomain.com *.trustedpartner.com;

        if ($invalid_referer) {
            # Option 1: Return a 403 Forbidden error
            return 403;
            # Option 2: Redirect to a placeholder image or a "hotlinking not allowed" image
            # rewrite ^ https://yourdomain.com/images/hotlink-forbidden.png break;
        }
        # Serve the file if referer is valid
        root /var/www/html;
    }

    # Other server configurations...
}


> **Pro Tip:** When configuring `valid_referers`, include `none` to allow direct access (e.g., typing the URL directly into the browser, or requests from some applications) and `blocked` to handle cases where browsers or privacy extensions strip the Referer header.

**Limitations:**
*   **Spoofing:** The `Referer` header can be easily spoofed by malicious users or automated scripts.
*   **Privacy Settings:** Some browsers or user privacy settings might block or strip the `Referer` header, leading to legitimate users being denied access.
*   **Proxies/VPNs:** Certain proxies or VPNs might also strip or alter the `Referer` header.
*   **Not Always Sent:** The `Referer` header is not always sent, especially with redirects or certain types of requests.

### 2.2. Method 2: Signed URLs (Temporary URLs)

**Signed URLs**, also known as pre-signed URLs or temporary URLs, provide a much stronger and more flexible hotlink protection mechanism. Instead of relying on a potentially unreliable HTTP header, signed URLs embed a cryptographic signature and an expiration timestamp directly into the resource's URL.

**How it works:**
1.  When a user requests a web page that contains your media (e.g., `yourdomain.com/article`), your backend server generates unique, time-limited URLs for each media asset on that page.
2.  These generated URLs contain parameters like an `Expires` timestamp and a `Signature` (or `Policy` and `Signature`) that has been cryptographically signed using a private key.
3.  The HTML page is rendered with these signed URLs (e.g., `<img src="https://cdn.yourdomain.com/my-image.jpg?Expires=1678886400&Signature=abcdefg...">`).
4.  When a browser requests the asset using this signed URL, your CDN or storage service (e.g., AWS S3, Google Cloud Storage, Cloudflare) validates the signature and checks the expiration time.
5.  If the signature is valid and the URL has not expired, the asset is served. Otherwise, access is denied.

**Conceptual Signed URL structure:**
`https://cdn.example.com/path/to/asset.jpg?Expires=<timestamp>&Key-Pair-Id=<id>&Signature=<cryptographic-signature>`

**Advantages:**
*   **Strong Security:** Cryptographic signatures are much harder to forge than HTTP headers.
*   **Fine-Grained Control:** You can specify an expiration time (seconds, minutes, hours), limit access to specific IP addresses, or even restrict it to a specific user or session.
*   **Works Everywhere:** Independent of browser `Referer` behavior.
*   **Temporary Access:** Ideal for premium content or resources that should only be accessible for a limited duration.

**Implementation Considerations:**
*   **Backend Integration:** Requires your backend application to generate these signed URLs for every media asset on every page load.
*   **Key Management:** Securely managing the private keys used for signing is crucial.
*   **CDN/Storage Service:** Most cloud storage providers (AWS S3, Google Cloud Storage, Azure Blob Storage) and CDNs (AWS CloudFront, Cloudflare, Akamai) offer native support for signed URLs.

python
# Conceptual Python code for generating a signed URL (using AWS S3 boto3 as an example)
import boto3
from datetime import datetime, timedelta

def generate_presigned_url(bucket_name, object_name, expiration=3600):
    """
    Generate a pre-signed URL to access an S3 object.
    :param bucket_name: S3 bucket name
    :param object_name: S3 object key
    :param expiration: URL expiration time in seconds (default 1 hour)
    :return: Pre-signed URL
    """
    s3_client = boto3.client('s3',
                             aws_access_key_id='YOUR_ACCESS_KEY',
                             aws_secret_access_key='YOUR_SECRET_KEY')
    try:
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': object_name},
                                                    ExpiresIn=expiration)
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return None
    return response

# Usage example
# signed_url = generate_presigned_url('my-media-bucket', 'images/hero.jpg', expiration=600) # Valid for 10 minutes
# print(signed_url)


## 3. Comparison / Trade-offs

Choosing between `Referer`-based protection and **Signed URLs** depends on your specific needs, security requirements, and the complexity you're willing to manage.

| Feature               | Referer-based Protection                                  | Signed URLs                                                         |
|-----------------------|-----------------------------------------------------------|---------------------------------------------------------------------|
| **Ease of Implementation** | Relatively simple, often involves web server/CDN configuration (e.g., Nginx, Apache, Cloudflare rules).    | More complex, requires backend application logic for generation and secure key management.   |
| **Security Level**    | Moderate. Susceptible to `Referer` spoofing; browser privacy settings can cause issues. | High. Cryptographically secure; very difficult to guess or forge.         |
| **Flexibility**       | Limited. Primarily blocks based on originating domain.    | High. Can specify expiration time, allowed IPs, specific users, download limits, etc.        |
| **Performance Impact**| Minimal on origin server/CDN edge. Primarily a header check. | Moderate. Backend needs to generate URLs for each request. CDN/storage service incurs validation overhead.       |
| **Use Cases**         | General public image/video hotlink prevention for static assets, basic protection. | Premium content, private user-generated content, time-limited access, secure downloads, assets requiring strict access control. |
| **Maintenance**       | Lower. Set-and-forget for the most part, though `valid_referers` lists may need updates. | Higher. Requires robust key rotation, expiration handling, and potential URL refresh logic.    |
| **Compatibility**     | Can be affected by browser privacy settings or network configurations that strip `Referer`. | Highly compatible as the signature is part of the URL itself.         |

## 4. Real-World Use Case

**Cloud Content Delivery Networks (CDNs) and Object Storage Services** are the backbone of modern web media delivery, and they heavily leverage these hotlink prevention techniques.

*   **AWS CloudFront (CDN) with S3 (Object Storage):** This combination is a prime example. For public websites, you might configure CloudFront to use **`Referer`-based restrictions** to prevent hotlinking of common assets. For more sensitive or premium content (e.g., a video streaming service), CloudFront supports **Signed URLs and Signed Cookies**.
    *   **Why?** A company like Netflix, while using highly sophisticated DRM, still relies on underlying CDN features like signed URLs (or similar token-based access) to ensure that direct links to their encrypted media segments are only valid for a specific user, session, and duration. This prevents casual sharing of media URLs and unauthorized access, significantly reducing bandwidth costs and protecting intellectual property.
*   **Google Cloud Storage and Cloudflare:** Both platforms offer similar capabilities. Google Cloud Storage allows **signed URLs** for accessing private objects. Cloudflare provides powerful **Hotlink Protection** rules (often `Referer`-based) at the edge, alongside more advanced features like **Signed Exchanges** and specific CDN rules that can incorporate JWTs (JSON Web Tokens) for authentication and authorization, akin to signed URLs.
    *   **Why?** Any platform hosting user-generated content, such as a photo-sharing site or a document management system, needs robust protection. Without it, users could directly link to sensitive files, or malicious actors could consume excessive bandwidth by embedding content on high-traffic sites. These solutions ensure that bandwidth is consumed only for legitimate access, typically from the platform's own authorized applications.

By understanding and implementing these techniques, you can effectively safeguard your resources, control costs, and maintain the integrity of your digital assets against unauthorized use.