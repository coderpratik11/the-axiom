---
# The layout must be 'page' for a custom list
layout: page

# Title appears in the sidebar
title: Roadmap

# This icon appears in the sidebar (FontAwesome)
icon: fas fa-stream

# The order in the sidebar (Home is 1, Categories is 2...)
order: 4

# The URL where this page lives
permalink: /roadmap/
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
