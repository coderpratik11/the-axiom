---
layout: default
title: Home
---

# 📚 Daily System Design

Welcome to my automated knowledge base.

## Latest Posts

<ul>
  {% for post in site.posts %}
    <li>
      <span style="color: #666; font-size: 0.8rem;">{{ post.date | date: "%Y-%m-%d" }}</span>
      <br>
      <a href="{{ post.url | relative_url }}" style="font-size: 1.2rem; font-weight: bold;">{{ post.title }}</a>
    </li>
    <br>
  {% endfor %}
</ul>
