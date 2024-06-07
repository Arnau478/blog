import os
import re
import yaml
import shutil
import commonmark

if os.path.exists("build"):
    shutil.rmtree("build")

os.mkdir("build")

shutil.copyfile("common.css", "build/common.css")

template_post = open("post.html").read()

for filename in os.listdir("posts"):
    file = open(os.path.join("posts", filename))
    out_file = open(os.path.join("build", filename.replace(".md", ".html")), "w+")

    md = file.read()
    frontmatter_text = re.search(r"---([\S\s]*?)---", md).group(1)
    md_no_frontmatter = re.sub(r"---[\S\s]*?---", "", md)

    frontmatter = yaml.load(frontmatter_text, Loader = yaml.CLoader)

    out = template_post

    out = out.replace("<%content%>", commonmark.commonmark(md_no_frontmatter))
    out = out.replace("<%title%>", frontmatter["title"])
    out = out.replace("<%date%>", str(frontmatter["date"]))

    out_file.write(out)
