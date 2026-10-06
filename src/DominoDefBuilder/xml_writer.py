import re
import xml.etree.ElementTree as ET
from collections import namedtuple

from .errors import BuildError

Node = namedtuple("Node", ["tag", "attrs", "children", "text"])


def formatAttr(value):
    if value is True:
        return "1"
    return str(value)


def normalizeColor(value):
    color = str(value).strip()
    if color.startswith("#"):
        color = color[1:]
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", color):
        raise BuildError("Invalid color %r: expected a six-digit RGB hex value" % value)
    return "#" + color.upper()


def node(tag, attrs=None, children=(), text=None):
    pairs = tuple(
        (
            key,
            normalizeColor(value) if key == "Color" else formatAttr(value),
        )
        for key, value in (attrs or {}).items()
        if value is not None and value is not False
    )
    return Node(
        tag, pairs, tuple(child for child in children if child is not None), text
    )


def attr(target, name, default=None):
    return dict(target.attrs).get(name, default)


def walk(root):
    yield root
    for child in root.children:
        for descendant in walk(child):
            yield descendant


def findAll(root, tag):
    return [item for item in walk(root) if item.tag == tag]


def toElement(source):
    element = ET.Element(source.tag, dict(source.attrs))
    element.text = source.text
    for child in source.children:
        element.append(toElement(child))
    return element


def serialize(root):
    element = toElement(root)
    ET.indent(element, space="    ")
    body = ET.tostring(element, encoding="unicode")
    text = '<?xml version="1.0" encoding="Shift_JIS"?>\n' + body + "\n"
    try:
        return text.encode("shift_jis")
    except UnicodeEncodeError as error:
        raise BuildError("Text cannot be encoded as Shift_JIS: " + str(error))
