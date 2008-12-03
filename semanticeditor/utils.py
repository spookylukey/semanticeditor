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

def remove_tag(tree, tag):
    """
    Remove all tags named tag from the tree.
    Their contents are pulled up into the parent.
    Returns true if the tree was changed.
    """

    cont = True
    while cont:
        children = list(tree.getchildren())
        changed = False
        for idx, node in enumerate(children):
            if node.tag == tag:
                tree.remove(node)
                # Insert its contents into parent.

                # 'text' is appended to older sibling's 'tail'
                #  or into 'text' of tree
                ntail = node.tail or ''
                ntext = node.text or ''

                if idx == 0:
                    ttext = tree.text or ''
                    tree.text = ttext + ntext
                else:
                    ctail = children[idx-1].tail or ''
                    children[idx-1].tail = ctail + ntext

                # Nodes are inserted
                for cidx, cnode in enumerate(node.getchildren()):
                    tree.insert(idx + cidx, cnode)

                # 'tail' is prepended to younger sibling's 'text'
                # or to 'tail' of tree
                if idx == len(children) - 1:
                    ttail = tree.tail or ''
                    tree.tail = ntail + ttail
                else:
                    ctext = children[idx+1].text or ''
                    children[idx+1].text = ntail + ctext

                # Everything has changed, so we start again
                changed = True
                break

        # if changed, we have to start over again.
        cont = changed

    # Recurse to children
    for n in tree.getchildren():
        remove_tag(n, tag)

def format_html(html, styleinfo):
    """
    Formats the XHTML given using a dictionary of style information.
    The dictionary has keys which are the names of headings,
    and values which are lists of CSS classes or special commands.
    Commands start with 'command:'
    """
    tree = parse(html)
    # Strip existing divs
    remove_tag(tree, 'div')

    return ET.tostring(tree).replace('<html>','').replace('</html>','')

