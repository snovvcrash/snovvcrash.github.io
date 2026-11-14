---
---
window.__POSTS = [{% for post in site.posts %}{"title":{{ post.title | jsonify }},"url":{{ post.url | jsonify }},"date":"{{ post.date | date: '%Y-%m-%d' }}","tags":{{ post.tags | jsonify }}}{% unless forloop.last %},{% endunless %}{% endfor %}];
