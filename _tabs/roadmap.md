---
layout: page
title: Roadmap
permalink: /roadmap/
icon: fas fa-map-signs  # Changed to a safe "Map" icon
order: 4
---

# 🗺️ Learning Roadmap

Here is the complete list of System Design questions we have covered so far.

<ul>
  {% for post in site.posts %}
    <li style="margin-bottom: 15px; list-style: none;">
      <span style="font-size: 0.85rem; color: #888; display:inline-block; min-width:100px;">
        <i class="far fa-calendar-alt"></i> {{ post.date | date: "%Y-%m-%d" }}
      </span>
      <a href="{{ post.url | relative_url }}" style="font-weight: 600; font-size: 1.1rem;">{{ post.title }}</a>
    </li>
    <hr style="opacity: 0.1; margin: 5px 0;">
  {% endfor %}
</ul>
