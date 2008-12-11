"""
ElementTree utils
"""

from elementtree import ElementTree as ET
from xml.parsers import expat

# ElementTree utilities

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
    """
    Return the parent of 'elem'.

    topnode is the node to start searching from
    """
    for n in topnode.getiterator():
        if elem in n.getchildren():
            return n
    return None

def get_index(parent, elem):
    """
    Return the index of elem in parent's children
    """
    return list(parent.getchildren()).index(elem)

def wrap_elements_in_tag(parent, start_idx, stop_idx, tag):
    """
    Wrap elements in parent at indices [start_idx:stop_idx] with
    a new element
    """
    newelem = ET.Element(tag)
    group = parent[start_idx:stop_idx]
    newelem[:] = group
    parent[start_idx:stop_idx] = [newelem]
    return newelem

