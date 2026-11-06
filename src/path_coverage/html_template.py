"""The HTML report's page templates, styles and scripts, kept as files in
html/ beside this one, and the filling of their slots."""

import re
from pathlib import Path

ASSETS = Path(__file__).parent / "html"


def asset(name):
    """The text of one of the report's template, style or script files."""
    return (ASSETS / name).read_text()


def page(name, **values):
    """The page template named name, its {{style}} the report's style
    sheet, and each other {{name}} values[name]."""
    return fill(asset(name), style=asset("style.css"), **values)


def fill(template, **values):
    """template with each {{name}} replaced by values[name]."""
    return re.sub(r"\{\{(\w+)\}\}", lambda match: values[match.group(1)], template)
