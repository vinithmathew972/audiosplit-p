import re

with open(r"AudioSplit-Pro\frontend\index.html", "r", encoding="utf-8") as f:
    text = f.read()

m = re.search(r'<main[^>]*>(.*?)</main>', text, re.DOTALL)
if m:
    children = re.findall(r'<(header|section|div)[^>]*class="([^"]*)"[^>]*id="?([^" >]*)', m.group(1))
    for tag, cls, id_ in children:
        print(f"Tag: <{tag}> class='{cls}' id='{id_}'")
