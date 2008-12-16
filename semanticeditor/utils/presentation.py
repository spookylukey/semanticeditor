"""
Utilities for manipulating the content provided by the user.
"""

from elementtree import ElementTree as ET
from semanticeditor.utils.etree import cleanup, flatten, get_parent, get_index, wrap_elements_in_tag
from xml.parsers import expat
import re

### Errors ###

class InvalidHtml(ValueError):
    pass

class IncorrectHeadings(ValueError):
    pass

class BadStructure(ValueError):
    pass

class TooManyColumns(BadStructure):
    pass

AllUserErrors = (InvalidHtml, IncorrectHeadings, BadStructure, TooManyColumns)

### Definitions ###

blockdef = set(['h1','h2','h3','h4','h5','h6', 'p', 'ol', 'ul', 'blockquote'])
headingdef = set(['h1','h2','h3','h4','h5','h6'])

MAXCOLS = 4
COLUMNCLASS = 'col'
ROWCLASSRE = re.compile('^row(\d+)col$')
ROWCLASS = 'row%dcol'

# The number of chars we trim block level elements to.
BLOCK_LEVEL_TRIM_LENGTH = 20
# TODO - trimming 

### Parsing ###

def parse(content):
    try:
        tree = ET.fromstring("<html>" + content + "</html>")
    except expat.ExpatError, e:
        raise InvalidHtml("HTML content is not well formed.")
    return tree

# NB: ElementTree is bizarre - after parsing some UTF-8 bytestrings,
# it will then return nodes that are 'str's if the text is all ASCII,
# otherwise 'unicode's (having correctly interpreted as UTF-8).  When
# serialising to JSON, this works out OK actually, so we leave it as
# is for the moment.

### Semantic editor functionality ###

## Presentation dictionary utilities

class PresentationInfo(object):
    """
    Encapsulates a piece of presentation information.
    """
    def __init__(self, prestype=None, name=None, verbose_name="", description=""):
        self.prestype = prestype
        self.name = name
        # The verbose_name and description are additional pieces of
        # information that are only needed when the client is
        # requesting a list of styles.  In other sitations these
        # objects may not have these attributes filled in.
        self.verbose_name = verbose_name
        self.description = description

    def __eq__(self, other):
        return self.prestype == other.prestype and self.name == other.name

    def __hash__(self):
        return hash(self.prestype) ^ hash(self.name)

    def __repr__(self):
        return "PresentationInfo(prestype=\"%s\", name=\"%s\")" % (self.prestype, self.name)

def PresentationClass(name, verbose_name="", description=""):
    """
    Shortcut for creating CSS classes
    """
    return PresentationInfo(prestype="class",  name=name,
                            verbose_name=verbose_name, description=description)

def PresentationCommand(name, verbose_name="", description=""):
    """
    Shortcut for creating commands
    """
    return PresentationInfo(prestype="command",  name=name,
                            verbose_name=verbose_name, description=description)

NEWROW = PresentationCommand('newrow',
                             verbose_name = "New row",
                             description = """
<p>Use this command to start a new row.</p>

<p>This must be used in conjunction with 'New column'
to create a column layout.</p>

<p>Please note that new rows and columns cannot be started at any
point in the document.  Within a given row, new columns can only be
started on section headings of the same level.  The 'New row' command
must be applied to the first section heading for which a column layout
is required and subsequent headings of the same level may be given
a 'New column' command.</p>

<p>If you wish to stop an existing column layout for a section, then you will
need to apply a 'New row' command to that section, creating a row with
just one column in it.</p>

""")

NEWCOL = PresentationCommand('newcol',
                             verbose_name = "New column",
                             description = """
<p>Use this command to start a new column, after a 'New row'
command has been used to start a set of columns.</p>

""")

## General utilities

def any(seq):
    for i in seq:
        if i:
            return True
    return False

def _invert_dict(d):
    return dict((v,k) for (k,v) in d.items())

def _get_classes_for_node(node):
    return filter(len, node.get('class','').split(' '))

def _find_next_available_name(stem, used_names):
    i = 2
    while True:
        attempt = stem + str(i)
        if attempt not in used_names:
            return attempt
        else:
            i += 1

def get_structure(root, assert_structure=False):
    """
    Return the heading nodes, as (level, name, tag, node) tuples
    """
    retval = []
    names = set()
    heading_names = set()
    cur_level = 1
    last_heading_num = 0
    for n in root.getiterator():
        if n.tag in blockdef:
            text = flatten(n)
            if n.tag in headingdef:
                name = text
                level = int(n.tag[1])
                cur_level = level
                if assert_structure:
                    if len(heading_names) == 0 and level > 1:
                        raise IncorrectHeadings("First heading must be H1.")

                    if name in heading_names:
                        raise IncorrectHeadings('There are duplicate headings with the name'
                                                ' "%s".' % name)

                    # Headings should decrease or monotonically increase
                    if level > last_heading_num + 1:
                        raise IncorrectHeadings('Heading "%(name)s" is level H%(foundnum)d,'
                                                ' but it should be level H%(rightnum)d or less' %
                                                dict(name=name,foundnum=level,rightnum=last_heading_num + 1))
                last_heading_num = level
                heading_names.add(name)
            else:
                name = text[0:BLOCK_LEVEL_TRIM_LENGTH]
                name = name + "..."
                if name in names:
                    name = _find_next_available_name(name, names)
                # Paragraphs etc within a section should be indented
                # one further than the heading above them.
                level = cur_level + 1
            names.add(name)
            retval.append((level, name, n.tag.upper(), n))

    return retval

## Main functions and sub functions

def extract_headings(content):
    """
    Extracts H1, H2, etc headings, and other block level elements and
    returns a list of tuples containing (level, name, tag)
    """
    # Parse
    tree = parse(content)
    structure = get_structure(tree, assert_structure=True)
    return [(l,name,tag) for (l,name,tag,node) in structure]

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


def format_html(html, styleinfo):
    """
    Formats the XHTML given using a dictionary of style information.
    The dictionary has keys which are the names of headings,
    and values which are lists of CSS classes or special commands.
    Commands start with 'command:', CSS classes start with 'class:'
    """
    root = parse(html)
    structure = get_structure(root, assert_structure=True)
    sectionnames = [name for (level, name, tag, node) in structure]
    styleinfo = _sanitise_styleinfo(styleinfo, sectionnames)

    # Strip existing divs, otherwise we cannot format properly.  If
    # there are other block level elements that mess things up, we
    # raise BadStructure later, but divs have no semantics so can just
    # be removed.
    _strip_presentation(root)
#    _assert_sane_sections(root, structure)

    section_nodes = {}
    headers = [(level,name,tag,h) for (level,name,tag,h) in structure
               if tag.lower() in headingdef]

    # Cut the HTML up into sections
    # First deal with headers only.  This makes life simple,
    # as headers always produce nested structures, and the
    # indexes passed to wrap_elements_in_tag don't need
    # adjusting for the changes we have made.
    for idx, (level, name, tag, node) in enumerate(headers):
        # We can no longer assume that parent = root, because the divs
        # we insert will change that.  However, the divs we insert
        # will keep sub-section headings on the same level.
        parent = get_parent(root, node)

        thisidx = get_index(parent, node)
        first_elem = thisidx

        # if a heading, then the 'scope' of each section is from
        # heading node to before the next heading with a level the
        # same or higher
        nextnodes = [(l,n) for (l,nname,t,n) in headers[idx+1:] if l <= level]
        if not nextnodes:
            # scope extends to end
            # Bug in elementtree - throws AssertionError if we try
            # to set a slice with [something:None]. So we use len()
            # instead of None
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
        section_nodes[name] = newdiv

    # Now deal with everything else
    for idx, (level, name, tag, node) in enumerate(structure):
        if tag.lower() not in headingdef:
            # Normal block level - these simply get a div that wraps
            # them.
            parent = get_parent(root, node)
            thisidx = get_index(parent, node)
            newdiv = wrap_elements_in_tag(parent, thisidx, thisidx + 1, "div")
            section_nodes[name] = newdiv

    # Apply normal CSS classes.
    for name, newdiv in section_nodes.items():
        # Apply css styles
        classes = [s.name for s in styleinfo[name] if s.prestype == "class"]
        classes.sort()
        if classes:
            newdiv.set("class", " ".join(classes))

    # Apply row/column commands
    _apply_commands(root, section_nodes, styleinfo, structure)

    return _html_extract(root)

def _html_extract(root):
    if len(root) == 0 and root.text is None and root.tail is None:
        return ''
    return ET.tostring(root).replace('<html>','').replace('</html>','')

def _strip_presentation(tree):
    cleanup(tree, lambda t: t.tag != 'div')


def _sanitise_styleinfo(styleinfo, sectionnames):
    # Replace lists with sets
    out = {}
    for k, v in styleinfo.items():
        out[k] = set(v)

    # Ensure that all sections have an entry in styleinfo
    for name in sectionnames:
        if not name in out:
            out[name] = set()

    return out

def _assert_sane_sections(root, structure):
    # First, all h1, h2 etc tags will be children of the root.
    # remove_tag should have ensured that, otherwise we will be unable
    # to cut the HTML into sections.
    for level, name, tag, h in structure:
        parent = get_parent(root, h)
        if tag.lower() in headingdef and parent is not root:
            raise BadStructure("Section heading \"%(name)s\" is not at the top level of "
                               "the document. This interferes with the ability to "
                               "format the sections and apply columns. "
                               "Please move the heading out of the '%(element)s'"
                               " element that contains it." % dict(name=name, element=parent.tag))

def _apply_commands(root, section_nodes, styleinfo, headers):
    # Rules:
    #  - No nesting of columns within columns
    #  - Within a given row, newcolumn must be applied to
    #    divs that are at the same level.
    #  - No columns allowed if newrow has not been started.

    # Headers has the sections in document order
    sections = [(level, name, section_nodes[name])
                for level, name, tag, n in headers]

    # Inverted dict
    known_nodes = _invert_dict(section_nodes)

    # Preprocess:
    #  - insert 'newcolumn' on everything that has 'newrow'
    for level, name, tag, hn in headers:
        if NEWROW in styleinfo[name]:
            styleinfo[name].add(NEWCOL)

    _add_rows_and_columns(root, known_nodes, styleinfo)
    # TODO: due to HTML/CSS quirks, we may need to add an empty <div
    # class="rowclear"> after every <div class="row">

def _assert_no_column_structure(node, known_nodes, styleinfo, current_level):
    # Check that no NEWROW/NEWCOL commands are found in the *children*
    # of node
    for n in node.getiterator():
        if n == node:
            continue
        name = known_nodes.get(n)
        if name is not None:
            commands = styleinfo[name]
            if NEWROW in commands or NEWCOL in commands:
                raise BadStructure("Heading '%(heading)s' has a 'New row' or 'New column' command applied to "
                                   "it, but it is at a section level %(level)s, which is lower than current "
                                   "column structure, which is defined at level %(curlevel)s." %
                                   dict(heading=name, level=n[0].tag, curlevel=current_level))


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

        if cur_row_start:
            # Rows/columns can only be added within the same level of
            # nesting of the HTML document.  This means we do not need
            # to recurse if we have started adding rows/columns.
            # However, it is helpful to recurse and check that no
            # NEWROW/COL commands were found, and complain to the user
            # if they are.
            _assert_no_column_structure(node, known_nodes, styleinfo,
                                        cur_row_start[0].tag)
        else:
            _add_rows_and_columns(node, known_nodes, styleinfo)

        # If we are at last node, and are still in a row, there won't
        # be a NEWROW command, so we have to close implicitly,
        # including the current node in the row (hence idx + 1).
        if idx == len(children) - 1 and cur_row_start is not None \
                and len(columns) > 0:
                _apply_row_col_divs(topnode, cur_row_start_idx + idx_offset, idx + 1 + idx_offset, columns)


def _apply_row_col_divs(parent, start_idx, stop_idx, columns):
    # Add the row
    newrow = wrap_elements_in_tag(parent, start_idx, stop_idx, 'div')
    newrow.set('class', ROWCLASS % len(columns))

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
        newcol.set('class', COLUMNCLASS)


def extract_presentation(html):
    """
    Return the presentation elements used to format some HTML,
    as a dictionary with keys = section names, values = set
    of classes/commands.
    """
    # TODO: this function is not brilliantly well defined e.g.  should
    # there be an entry in the dictionary for sections with no
    # formatting?  This does not affect functionality, but it does
    # affect tests.

    root = parse(html)
    structure = get_structure(root)
    pres = {}
    for level, name, tag, node in structure:
        pres[name] = set()
        section_node = get_parent(root, node)
        if section_node is None or section_node.tag != 'div':
            # Not in standard format, we can't say anything about it
            continue

        # Section - extract classes
        for c in _get_classes_for_node(section_node):
            pres[name].add(PresentationClass(c))

        # Parent/grandparent of section - newcol/newrow
        p = get_parent(root, section_node)
        if p is not None and p.tag == 'div':
            # We only care if section_node is the first child of the div
            if get_index(p, section_node) == 0:
                classes = _get_classes_for_node(p)
                if COLUMNCLASS in classes:
                    pres[name].add(NEWCOL)
                gp = get_parent(root, p)
                if gp is not None and gp.tag == 'div':
                    if any(ROWCLASSRE.match(c) is not None for c in _get_classes_for_node(gp)) \
                            and get_index(gp, p) == 0:
                        pres[name].add(NEWROW)
                        pres[name].discard(NEWCOL) # for tidiness, not technically necessary

    _strip_presentation(root)
    out_html = _html_extract(root)

    return (pres, out_html)
