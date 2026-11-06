"""The HTML report's pages, from a copy of the shared renderer,
html-reporter, kept in html/ beside this file: each page is page.html, its
data inline, drawn in the browser by render.js."""

import json
import re
from pathlib import Path

ASSETS = Path(__file__).parent / "html"


def asset(name):
    """The text of one of the renderer's files."""
    return (ASSETS / name).read_text()


def page(data):
    """The page drawing data, as page_data gives it: the template
    pages.json names, its style the style sheet, its data the data, and its
    script the scripts its kind of page runs. Example: page_data.index's
    data gives the index page."""
    pages = json.loads(asset("pages.json"))
    scripts = "".join(asset(name) for name in pages["scripts"][data["page"]])
    return fill(asset(pages["template"]), style=asset(pages["style"]), data=inline(data), script=scripts)


def inline(data):
    """data as JSON to put inside a script, every </ written <\\/ so no
    string in it can close the script. Example: a text of </script> is
    written <\\/script>."""
    return json.dumps(data).replace("</", "<\\/")


def fill(template, **values):
    """template with each {{name}} replaced by values[name]."""
    return re.sub(r"\{\{(\w+)\}\}", lambda match: values[match.group(1)], template)
