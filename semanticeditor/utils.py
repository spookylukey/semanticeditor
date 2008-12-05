"""
Utilities for manipulating the content provided by the user.
"""

from elementtree import ElementTree as ET
from xml.parsers import expat

class InvalidHtml(ValueError):
    pass

class IncorrectHeadings(ValueError):
    pass

class BadStructure(ValueError):
    pass

class TooManyColumns(BadStructure):
    pass

headingdef = ['h1','h2','h3','h4','h5','h6']
NEWROW = 'command:newrow'
NEWCOL = 'command:newcolumn'

MAXCOLS = 4

def _is_command(x):
    return x.startswith('command:')

def _get_class(x):
    return x[6:]

def _is_class(x):
    return x.startswith('class:')

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
            raise IncorrectHeadings('Heading "%(name)s" is level H%(foundnum)d,'
                                    ' but it should be level H%(rightnum)d or less' %
                                    dict(name=name,foundnum=num,rightnum=lastnum+1))
        lastnum = num
        if name in names:
            raise IncorrectHeadings('There are duplicate headings with the name'
                                    ' "%s".' % name)
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

def _assert_sane_sections(root, headers):
    # First, all h1, h2 etc tags will be children of the root.
    # remove_tag should have ensured that, otherwise we will be unable
    # to cut the HTML into sections.
    for level, name, h in headers:
        parent = get_parent(root, h)
        if parent is not root:
            raise BadStructure("Section heading \"%(name)s\" is not at the top level of "
                               "the document. This interferes with the ability to "
                               "format the sections and apply columns. "
                               "Please move the heading out of the '%(element)s'"
                               " element that contains it." % dict(name=name, element=parent.tag))

def _invert_dict(d):
    return dict((v,k) for (k,v) in d.items())

def _apply_commands(root, section_nodes, styleinfo, headers):
    # Rules:
    #  - No nesting of columns within columns
    #  - Within a given row, newcolumn must be applied to
    #    divs that are at the same level.
    #  - No columns allowed if newrow has not been started.

    # Headers has the sections in document order
    sections = [(level, name, section_nodes[name])
                for level, name, n in headers]

    # Inverted dict
    known_nodes = _invert_dict(section_nodes)

    # Preprocess:
    #  - insert 'newcolumn' on everything that has 'newrow'
    for level, name, hn in headers:
        if NEWROW in styleinfo[name]:
            styleinfo[name].add(NEWCOL)

    _add_rows_and_columns(root, known_nodes, styleinfo)
    # TODO: due to HTML/CSS quirks, we may need to add an empty <div
    # class="rowclear"> after every <div class="row">

def _add_rows_and_columns(topnode, known_nodes, styleinfo):
    cur_row_start = None
    cur_col = None
    children = list(topnode.getchildren())
    # Offset used to cope with the fact that we are pulling sub-nodes
    # out of topnode as we go along.
    idx_offset = 0
    for idx, node in enumerate(children):
        name = known_nodes.get(node)
        if name is None:
            # If not a section node, it cannot contain sections.
            # or have commands
            continue
        commands = styleinfo[name]

        if NEWROW in commands:
            if cur_row_start is not None:
                # The previous row is finished
                _apply_row_col_divs(topnode, cur_row_start_idx + idx_offset, idx + idx_offset, columns)
                # We have removed (idx - cur_row_start_idx) elements,
                # and added one back
                idx_offset += -(idx - cur_row_start_idx) + 1
            # start a new row
            cur_row_start = node
            cur_row_start_idx = idx
            columns = []

        if NEWCOL in commands:
            if cur_row_start is None:
                raise BadStructure("'New column' command was found on section "
                                   "'%(name)s' without an appropriate 'new row' "
                                   "command before it. " % dict(name=name))
            else:
                columns.append((idx + idx_offset, name))

        if not cur_row_start:
            # Rows/columns can only be added within the same level of nesting
            # of the HTML document.  This means we do not need to recurse if
            # we have started adding rows/columns.
            _add_rows_and_columns(node, known_nodes, styleinfo)
            # However, it would be good to recurse and check that no
            # NEWROW/COL commands were found, and warn the user if
            # they are.

        # If we are at last node, and are still in a row, there won't
        # be a NEWROW command, so we have to close implicitly,
        # including the current node in the row (hence idx + 1).
        if idx == len(children) - 1 and cur_row_start is not None \
                and len(columns) > 0:
                _apply_row_col_divs(topnode, cur_row_start_idx + idx_offset, idx + 1 + idx_offset, columns)


def _apply_row_col_divs(parent, start_idx, stop_idx, columns):
    # Add the row
    newrow = wrap_elements_in_tag(parent, start_idx, stop_idx, 'div')
    newrow.set('class', 'row%dcol' % len(columns))

    # Add the columns
    if len(columns) > MAXCOLS:
        raise TooManyColumns("The maximum number of columns is %(max)d. "
                             "Please move section '%(name)s' into a new "
                             "row." % dict(max=MAXCOLS, name=columns[MAXCOLS][1]))

    # The idx in 'columns' are all out now, due to having pulled the
    # nodes out. Fix them up, and add a dummy entry to provide the
    # 'stop_idx' for the last column.
    columns = [(idx - start_idx, node) for (idx, node) in columns]
    columns.append((stop_idx - start_idx, None))

    # Go in reverse order, so that indices are not invalidated
    columns.reverse()
    for i, (idx, node) in enumerate(columns):
        if node is None:
            # last dummy entry
            continue
        newcol = wrap_elements_in_tag(newrow, idx, columns[i - 1][0], 'div')
        newcol.set('class', 'col')


def _sanitise_styleinfo(styleinfo, headingnames):
    # Replace lists with sets
    out = {}
    for k, v in styleinfo.items():
        out[k] = set(v)

    # Ensure that all sections have an entry in styleinfo
    for level, name in headingnames:
        if not name in out:
            out[name] = set()

    return out

# == Formatting HTML ==
#
# The user is allowed to assign presentation to different sections.
# The sections are identified by headings, so that formatting will be
# consistent with the logical structure of the document.
#
# This imposes a certain div structure on the HTML.  Consider the following
# document:
#
# - H1 - Section 1
#   - H2 - Section 1.1
#   - P
#   - H2 - Section 1.2
# - H1 - Section 2
#   etc
#
# If the user wants 'Section 1' in a blue, bordered box, the only
# (practical) way to do it in CSS is to create a div around *all* of
# section 1 (including Section 1.1 and Section 1.2) and apply a CSS
# class to it. The div structures must therefore nest according to the
# logical structure of the document.
#
# If the user decided that column 1 should contain Section 1 up to
# Section 1.1, and that column 2 should contain Section 1.2 up to
# Section 2, this would require a div structure incompatible with the
# above. Thus the column layout is limited by the logical structure of
# the document.

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

def format_html(html, styleinfo):
    """
    Formats the XHTML given using a dictionary of style information.
    The dictionary has keys which are the names of headings,
    and values which are lists of CSS classes or special commands.
    Commands start with 'command:', CSS classes start with 'class:'
    """
    # Ensure that the headings are well formed and the HTML is valid
    headingnames = extract_headings(html)

    styleinfo = _sanitise_styleinfo(styleinfo, headingnames)

    root = parse(html)

    # Strip existing div, otherwise we cannot format properly.  If
    # there are other block level elements that mess things up, we
    # raise BadStructure later, but divs have so semantics so can just
    # be removed.
    cleanup(root, lambda t: t.tag != 'div')

    # Get the heading nodes, decorated with the level of the heading
    headers = [(int(n.tag[1]), flatten(n), n) for n in root.getiterator() if n.tag in headingdef]

    _assert_sane_sections(root, headers)

    section_nodes = {}
    # Cut the HTML up into sections
    for idx, (level, name, h) in enumerate(headers):
        # We can no longer assume that parent = root, because the divs
        # we insert will change that.  However, the divs we insert
        # will keep sub-section headings on the same level.
        parent = get_parent(root, h)

        thisidx = get_index(parent, h)
        first_elem = thisidx

        # 'scope' of each section is from heading node to before the next
        # heading with a level the same or higher
        nextnodes = [(l,n) for (l,nname,n) in headers[idx+1:] if l <= level]
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

        newdiv = wrap_elements_in_tag(parent, first_elem, last_elem, "div")

        # Apply css styles
        classes = [_get_class(s) for s in styleinfo[name] if _is_class(s)]
        classes.sort()
        if classes:
            newdiv.set("class", " ".join(classes))

        section_nodes[name] = newdiv

    _apply_commands(root, section_nodes, styleinfo, headers)

    return ET.tostring(root).replace('<html>','').replace('</html>','')

