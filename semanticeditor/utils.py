"""
Utilities for manipulating the content provided by the user.
"""

from elementtree import ElementTree as ET
from xml.parsers import expat

class InvalidHtml(ValueError):
    pass

class IncorrectHeadings(ValueError):
    pass


headingdef = ['h1','h2','h3','h4','h5','h6']


def parse(content):
    try:
        tree = ET.fromstring("<html>" + content + "</html>")
    except expat.ExpatError, e:
        raise InvalidHtml("HTML content is not well formed.")
    return tree


def extract_headings(content):
    """
    Extracts H1, H2, etc headings, and returns a list of tuples
    containing (level, name)
    """
    # Parse
    tree = parse(content)
    nodes = [n for n in tree.getiterator() if n.tag in headingdef]
    headings = [(int(h.tag[1]), flatten(h)) for h in nodes]

    # Check ordering
    if len(headings) > 0 and headings[0][0] > 1:
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
            raise IncorrectHeadings('There are duplicate headings with the name "%s".' % name)
        names[name] = True

    return headings

def textjoin(a, b):
    a = a or ''
    b = b or ''
    return a + b

def cleanup(elem, filter):
    """
    Removes start and stop tags for any element for which the filter
    function returns false.  If you want to remove the entire element,
    including all subelements, use the 'clear' method inside the
    filter callable.

    Note that this function modifies the tree in place.
    @param elem An element tree.
    @param filter An filter function.  This should be a callable that
    takes an element as its single argument.
    """

    out = []
    for e in elem:
        cleanup(e, filter)
        if not filter(e):
            if e.text:
                if out:
                    out[-1].tail = textjoin(out[-1].tail, e.text)
                else:
                    elem.text = textjoin(elem.text, e.text)
            out.extend(e)
            if e.tail:
                if out:
                    out[-1].tail = textjoin(out[-1].tail, e.tail)
                else:
                    elem.text = textjoin(elem.text, e.tail)
        else:
            out.append(e)
    elem[:] = out

def flatten(elem):
    text = elem.text or ""
    for e in elem:
        text += flatten(e)
        if e.tail:
            text += e.tail
    return text

def format_html(html, styleinfo):
    """
    Formats the XHTML given using a dictionary of style information.
    The dictionary has keys which are the names of headings,
    and values which are lists of CSS classes or special commands.
    Commands start with 'command:'
    """
    tree = parse(html)
    # Strip existing divs
    cleanup(tree, lambda t: t.tag != 'div')

    return ET.tostring(tree).replace('<html>','').replace('</html>','')

