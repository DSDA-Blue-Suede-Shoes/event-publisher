from typing import Iterable

from bs4 import Tag, PageElement, NavigableString

type_props = {
    "#text": {},
    "b": {'bold': True},
    "strong": {'bold': True},
    "h1": {'bold': True, 'line': 2, 'push': True},
    "h2": {'bold': True, 'line': 2, 'push': True},
    "h3": {'bold': True, 'line': 2, 'push': True},
    "h4": {'bold': True, 'line': 2, 'push': True},
    "h5": {'bold': True, 'line': 2, 'push': True},
    "i": {'italic': True},
    "em": {'italic': True},
    "sup": {'super': True},
    'li': {'line': 1, 'pre_text': " • ", 'push': True},
    'br': {'line': 1, 'push': True},
    'p': {'line': 2, 'push': True},
    'video': {'line': 1, 'push': True},
    'tr': {'pre_text': "| ",'line': 1, 'push': True},
    'td': {'post_text': " | "},
    'th': {'post_text': " | "},
    'img': {'attr': "src", 'push': True},
    'a': {'attr': "href"},
}

class_props = {
    "knewave": {'bold': True, 'italic': True},
    "indansen": {'bold': True, 'italic': True},
}


def trim_list(element_list: list) -> list:
    """
    Trims breaks off the start and end

    :param element_list: Untrimmed list
    :return: Trimmed list
    """
    trim_index = 0
    for i in range(len(element_list)):
        if element_list[i]['text'].strip() != "":
            trim_index = i
            break

    element_list = element_list[trim_index:]

    for i in range(len(element_list)-1, 0, -1):
        if element_list[i]['text'].strip() != "":
            trim_index = i
            break

    element_list = element_list[0:trim_index + 1]
    return element_list


# Todo: process links
def get_list(nodes: Iterable[Tag] | Iterable[PageElement], node_list: list = None, properties: dict = None):
    """
    Takes a collection of nodes and uses that to build a list of text elements with properties.

    :param nodes: Input
    :param node_list: Current output list (for recursion)
    :param properties: Properties to pass for recursion
    :return: List of text elements with properties
    """
    if properties is None:
        properties = {}
    if node_list is None:
        node_list = []

    for node in nodes:
        new_props = dict(properties)
        new_props['line'] = 0
        new_props['push'] = False
        text = ""

        new_props.update(type_props.get(node.name, {}))
        if hasattr(node, "get"):
            class_list = node.get("class", [''])
            for c in class_list:
                new_props.update(class_props.get(c, {}))
        text = new_props.get('pre_text', "")

        if new_props.get('attr') and hasattr(node, "get"):
            if new_props['push']:
                # For images etc., just post source
                text += node.get(new_props['attr'])
            elif node.text != node.get(new_props['attr']):
                # For links etc., do this, but only if the link text is not the link itself, that looks stupid.
                new_props['post_text'] = f" ({node.get(new_props['attr'])})"

        if type(node) is NavigableString:
            text = node.text.replace('\n', '')
            text += new_props.get('post_text', "")
            if text:
                node_list.append({'text': text, 'node': node, 'properties': new_props})
        elif new_props['push']:
            node_list.append({'text': text, 'node': None, 'properties': new_props})
            new_props['pre_text'] = ""
        if hasattr(node, 'children'):
            get_list(node.children, node_list, new_props)
    return node_list


def super_transform(text: str) -> str:
    """
    Transforms text to unicode super characters

    :param text: Text to transform
    :return:
    """
    new_text = ""
    lookup = {
        's': 'ˢ',
        't': 'ᵗ',
        'h': 'ʰ',
        'r': 'ʳ',
        'd': 'ᵈ',
        'n': 'ⁿ'
    }
    for c in text:
        new_c = lookup.get(c, c)
        new_text += new_c
    return new_text


def unicode_transform(text: str, uc_base: int, lc_base: int):
    """
    Transforms a given string from ASCII range to a given unicode range.

    :param text: String to transform
    :param uc_base: Char-code of the 'A' in the range
    :param lc_base: Char-code of the 'a' in the range
    :return: Output string with unicode characters
    """
    new_text = ""
    for c in text:
        char_code = ord(c)
        if ord('A') <= char_code <= ord('Z'):
            new_text += chr(uc_base + char_code - ord('A'))
        elif ord('a') <= char_code <= ord('z'):
            new_text += chr(lc_base + char_code - ord('a'))
        else:
            new_text += c

    return new_text


def render_unicode(element_list: list) -> str:
    out = ""

    for el in element_list:
        text = el['text']
        for i in range(el['properties']['line']):
            out += "\n"

        if el['properties'].get('super'):
            text = super_transform(text)
        elif el['properties'].get('bold') and el['properties'].get('italic'):
            text = unicode_transform(text, ord('𝘼'), ord('𝙖'))
        elif el['properties'].get('bold'):
            text = unicode_transform(text, ord('𝗔'), ord('𝗮'))
        elif el['properties'].get('italic'):
            text = unicode_transform(text, ord('𝘈'), ord('𝘢'))

        out += text
    return out


def render_whatsapp(element_list: list) -> str:
    out = ""

    for el in element_list:
        text = el['text']
        for i in range(el['properties']['line']):
            out += "\n"

        if text:
            if el['properties'].get('bold'):
                text = f"*{text}*"

            if el['properties'].get('italic'):
                text = f"_{text}_"

            if el['properties'].get('super'):
                text = super_transform(text)

        out += text
    return out
