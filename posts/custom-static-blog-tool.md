---
title: A custom static blog tool
date: 2024-06-07
---

I wanted to make my own blog for a long time, but couldn't decide on what static page tool to use. I considered Jekyll and Hugo, but they both seem to be quite bloated. So I made my own.

The tool is by no means a general-purpose static page generator, it is made to suit my needs. And where is it? Well, here it is. This page was generated using a small tool written in python.

It takes a template file:
```html
<html>
    <body>
        <h1><%title%></h1>
        <%content%>
    </body>
</html>
```
and replaces things like `<%title%>` with the appropriate value. The `<%content%>` tag is replaced with the rendered markdown.

It supports the following things for now:

- **Frontmatter**: Posts can have a frontmatter, where things like the post title and date are specified. It follows the YAML format.

- **Code embeds**: It supports code embeds via `` ` `` and `` ``` ``. The only catch is syntax highlighting, which is still not supported.

That's all for today. You can see the source code and follow the development of the tool (and the blog) over at <https://github.com/Arnau478/blog>.
