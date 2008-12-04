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

def get_parent(topnode, elem):
    for n in topnode.getiterator():
        if elem in n.getchildren():
            return n
    return None

def get_index(parent, elem):
    return list(parent.getchildren()).index(elem)

def format_html(html, styleinfo):
    """
    Formats the XHTML given using a dictionary of style information.
    The dictionary has keys which are the names of headings,
    and values which are lists of CSS classes or special commands.
    Commands start with 'command:', CSS classes start with 'class:'
    """
    # Ensure that the headings are well formed and the HTML is valid
    headingnames = extract_headings(html)

    root = parse(html)

    # Strip existing divs
    cleanup(root, lambda t: t.tag != 'div')

    # Get the heading nodes, decorated with the level of the heading
    headers = [(int(n.tag[1]), n) for n in root.getiterator() if n.tag in headingdef]


    # First, all h1, h2 etc tags will be children of the root.
    # remove_tag should have ensured that, otherwise we will be unable
    # to cut the HTML into sections.
    for level, h in headers:
        parent = get_parent(root, h)
        # TODO: nicer assert
        assert parent is root

    # Cut the HTML up into sections
    for idx, (level, h) in enumerate(headers):
        name = flatten(h)
        # We can no longer assume that parent = root, because the divs
        # we insert will change that.  However, the divs we insert
        # will keep sub-section headings on the same level.
        parent = get_parent(root, h)

        thisidx = get_index(parent, h)
        first_elem = thisidx

        # 'scope' of each section is from heading node to before the next
        # heading with a level the same or higher
        nextnodes = [(l,n) for (l,n) in headers[idx+1:] if l <= level]
        # Bug in elementtree - throws AssertionError if we try
        # to set a slice with [something:None]. So we use len()
        # instead of None
        if not nextnodes:
            # scope extends to end
            last_elem = len(parent)
        else:
            # scope extends to node before n
            nextnode = nextnodes[0][1]
            nn_parent = get_parent(root, nextnode)
            if nn_parent is parent:
                # Same level, can find index
                last_elem = get_index(parent, nextnode)
            else:
                # Different level, (due to having been enclosed in a
                # div already), just go to end
                last_elem = len(parent)

        group = parent[first_elem:last_elem]

        # Create a new div for them
        newdiv = ET.Element("div")
        newdiv[:] = group

        # Replace original element
        parent[first_elem:last_elem] = [newdiv]

        # Apply css styles
        classes = [s[6:] for s in styleinfo.get(name, []) if s.startswith("class:")]
        if classes:
            newdiv.set("class", " ".join(classes))
        # TODO - apply styles
        # TODO - store div for later processing

    # TODO - apply commands to divs

    return ET.tostring(root).replace('<html>','').replace('</html>','')

