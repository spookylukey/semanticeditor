"""
Utilities for manipulating the content provided by the user.
"""

from elementtree import ElementTree as ET
from xml.parsers import expat

class InvalidHtml(ValueError):
    pass

class IncorrectHeadings(ValueError):
    pass

def extract_headings(content):
    """
    Extracts H1, H2, etc headings, and returns a list of tuples
    containing (level, name)
    """
    try:
        tree = ET.fromstring("<html>" + content + "</html>")
    except expat.ExpatError, e:
        raise InvalidHtml("HTML content is not well formed.")

    headingdef = ['h1','h2','h3','h4','h5','h6']

    # Parse
    nodes = [n for n in tree.getiterator() if n.tag in headingdef]
    headings = [(int(h.tag[1]), flatten(h)) for h in nodes]

    # Check ordering
    if len(headings) == 0:
        return headings

    if headings[0][0] > 1:
        raise IncorrectHeadings("First heading must be H1.")

    # Headings should decrease or monotonically increase
    # and they should have unique names
    lastnum = 0
    names = {}
    for num, name in headings:
        if num > lastnum + 1:
            raise IncorrectHeadings('Heading "%(name)s" is level H%(foundnum)d, but it should be level H%(rightnum)d or less'  % dict(name=name,foundnum=num,rightnum=lastnum+1))
        lastnum = num
        if name in names:
            raise IncorrectHeadings('There are more than one headings with the name "%s".' % name)
        names[name] = True

    return headings


def flatten(node):
    """
    Pulls out all text in this node and its children.
    """
    # Use flatten_helper, but don't include the
    # tail for the very top level element
    return flatten_helper(node, include_tail=False)

def flatten_helper(node, include_tail=True):
    if include_tail:
        tail = node.tail or ''
    else:
        tail = ''
    return node.text + ''.join(map(flatten_helper, node.getchildren())) + tail
