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
template_index = open("index.html").read()

index_out = template_index
index_post_item_reg = re.search(r"(<%post{%>([\S\s]*)<%}post%>)", index_out)
index_post_item_template = index_post_item_reg.group(2)
index_post_content = ""

index_file = open(os.path.join("build", "index.html"), "w+")

for filename in reversed(os.listdir("posts")):
    file = open(os.path.join("posts", filename))

    md = file.read()
    frontmatter_text = re.search(r"---([\S\s]*?)---", md).group(1)
    md_no_frontmatter = re.sub(r"---[\S\s]*?---", "", md)

    filename_reg = re.search(r"((\d*?)-(\d*?)-(\d*?))-(.*).md", filename)
    date = filename_reg.group(1)
    name = filename_reg.group(5)
    print(f"Generating {name}... ", end="")

    out_file = open(os.path.join("build", name + ".html"), "w+")

    frontmatter = yaml.load(frontmatter_text, Loader = yaml.CLoader)

    out = template_post

    out = out.replace("<%content%>", commonmark.commonmark(md_no_frontmatter))
    out = out.replace("<%title%>", frontmatter["title"])
    out = out.replace("<%date%>", date)

    out_file.write(out)

    index_post_item_content = index_post_item_template
    index_post_item_content = index_post_item_content.replace("<%title%>", frontmatter["title"])
    index_post_item_content = index_post_item_content.replace("<%url%>", name + ".html")
    index_post_item_content = index_post_item_content.replace("<%date%>", date)
    index_post_content += index_post_item_content

    print("done")

index_out = index_out.replace(index_post_item_reg.group(1), index_post_content)

index_file.write(index_out)
