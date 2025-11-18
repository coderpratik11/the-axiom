---
layout: page
title: Roadmap
permalink: /roadmap/
icon: fas fa-list-ul
order: 3
---

# 🗺️ Learning Roadmap

Here is the complete list of System Design questions we have covered so far.

<ul>
  {% for post in site.posts %}
    <li style="margin-bottom: 10px;">
      <span style="font-size: 0.85rem; color: #888; display:inline-block; width:90px;">{{ post.date | date: "%Y-%m-%d" }}</span>
      <a href="{{ post.url | relative_url }}" style="font-weight: 500;">{{ post.title }}</a>
    </li>
  {% endfor %}
</ul>
