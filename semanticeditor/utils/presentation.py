"""
Utilities for manipulating the content provided by the user.
"""

from elementtree import ElementTree as ET
from semanticeditor.utils.etree import cleanup, flatten, get_parent, get_index, wrap_elements_in_tag, indent
from semanticeditor.utils.datastructures import struct
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

# The number of chars we trim block level elements to.
BLOCK_LEVEL_TRIM_LENGTH = 20

### Layout CSS class names ###

# This is designed to be user supplyable if necessary

class LayoutDetails(object):
    ROW_CLASS = "row"
    COLUMN_CLASS = "column"

    def row_classes(self, column_count):
        """
        Returns a list of CSS classes to be used for a row
        containing column_count columns
        """
        return [self.ROW_CLASS, "columns%d" % column_count]

    def column_classes(self, column_num, column_count):
        """
        Returns the CSS class to be used for a column
        which is number column_num out of column_count.
        """
        retval = [self.COLUMN_CLASS]
        if column_num == 1:
            retval.append("firstcolumn")
        if column_num == column_count:
            retval.append("lastcolumn")
        return retval

    def is_row_class(self, classes):
        """
        Returns true if the classes (list of strings) correspond
        to the classes used for a row.
        """
        return self.ROW_CLASS in classes

    def is_column_class(self, classes):
        """
        Returns true if the classes (list of strings) correspond
        to the classes used for a column.
        """
        return self.COLUMN_CLASS in classes

    def row_end_html(self):
        """
        Returns some raw HTML to be added at the end of a row
        (e.g. for clearing floats) if necessary.
        """
        return ""

### Parsing ###
import htmlentitydefs
def fixentities(htmltext):
    # replace HTML character entities with numerical references
    # note: this won't handle CDATA sections properly
    def repl(m):
        entity = htmlentitydefs.entitydefs.get(m.group(1).lower())
        if not entity:
            return m.group(0)
        elif len(entity) == 1:
            if entity in "&<>'\"":
                return m.group(0)
            return "&#%d;" % ord(entity)
        else:
            return entity
    return re.sub("&(\w+);?", repl, htmltext)

def parse(content):
    try:
        tree = ET.fromstring("<html>" + fixentities(content) + "</html>")
    except expat.ExpatError, e:
        raise InvalidHtml("HTML content is not well formed.")
    return tree

# NB: ElementTree is bizarre - after parsing some UTF-8 bytestrings,
# it will then return nodes that are 'str's if the text is all ASCII,
# otherwise 'unicode's (having correctly interpreted the UTF-8).  When
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

def make_sect_id(tag, used_ids):
    i = 1
    while True:
        attempt = tag + "_" + str(i)
        if attempt not in used_ids:
            return attempt
        else:
            i += 1

def get_layout_details_strategy():
    # TODO - make configurable
    return LayoutDetails()


class StructureItem(object):
    __metaclass__ = struct
    level = 0     #    level is the 'outline level' in the document i.e. an integer
    sect_id = ''  #    sect_id is a unique ID used for storing presentation information against
    name = ''     #    name is a user presentable name for the section
    tag = ''      #    tag is the HTML element e.g. H1
    node = None   #    node is the ElementTree node


def get_structure(root, assert_structure=False):
    """
    Return the structure nodes, as a list of StructureItems
    """
    retval = []
    names = set()
    sect_ids = set()
    heading_names = set()
    cur_level = 1
    last_heading_num = 0
    first_heading_level = 1
    for n in root.getiterator():
        if n.tag in blockdef:
            text = flatten(n)
            sect_id = n.get('id', '')
            if sect_id == '' or not sect_id.startswith(n.tag):
                sect_id = make_sect_id(n.tag, sect_ids)
            sect_ids.add(sect_id)
            if n.tag in headingdef:
                name = text
                level = int(n.tag[1])
                cur_level = level
                if assert_structure:
                    if len(heading_names) == 0:
                        first_heading_level = level
                    else:
                        if level < first_heading_level:
                            raise IncorrectHeadings("No heading can be higher than the first "
                                                    "heading, which was H%d." %
                                                    first_heading_level)

                    if name in heading_names:
                        raise IncorrectHeadings('There are duplicate headings with the name'
                                                ' "%s".' % name)

                    # Headings should decrease or monotonically increase
                    if len(heading_names) > 0 and level > last_heading_num + 1:
                        raise IncorrectHeadings('Heading "%(name)s" is level H%(foundnum)d, '
                                                'but it should be level H%(rightnum)d or less' %
                                                dict(name=name,foundnum=level,
                                                     rightnum=last_heading_num + 1))
                last_heading_num = level
                heading_names.add(name)
            else:
                name = text[0:BLOCK_LEVEL_TRIM_LENGTH]
                name = name + "..."
                if name in names:
                    name = _find_next_available_name(name, names)
                # Paragraphs etc within a section should be indented
                # one further than the heading above them.
                if len(heading_names) == 0:
                    level = 1
                else:
                    level = cur_level + 1
            names.add(name)
            # Level is adjusted so that e.g. H3 is level 1, if it is
            # the first to appear in the document.
            retval.append(StructureItem(level=level - first_heading_level + 1,
                                        sect_id=sect_id,
                                        name=name,
                                        tag=n.tag.upper(),
                                        node=n))

    return retval

## Main functions and sub functions

def extract_structure(content):
    """
    Extracts H1, H2, etc headings, and other block level elements and
    returns a list of tuples containing (level, name, tag)
    """
    # Parse
    tree = parse(content)
    structure = get_structure(tree, assert_structure=True)
    return structure

# == Formatting HTML ==
#
# The user is allowed to assign presentation to different sections and block
# elements, including use of 'new row' and 'new column' commands.

def format_html(html, styleinfo, return_tree=False, pretty_print=False):
    """
    Formats the XHTML given using a dictionary of style information.
    The dictionary has keys which are the names of headings,
    and values which are lists of CSS classes or special commands.
    """
    layout_strategy = get_layout_details_strategy()
    root = parse(html)
    structure = get_structure(root, assert_structure=True)
    sect_ids = [s.sect_id for s in structure]
    styleinfo = _sanitise_styleinfo(styleinfo, sect_ids)

    # Strip existing divs, otherwise we cannot format properly.  If
    # there are other block level elements that mess things up, we
    # raise BadStructure later, but divs have no semantics so can just
    # be removed.
    _strip_presentation(root)
    _assert_sane_sections(root, structure)

    # Apply normal CSS classes.
    for si in structure:
        # Apply css styles
        classes = [s.name for s in styleinfo[si.sect_id] if s.prestype == "class"]
        classes.sort()
        if classes:
            si.node.set("class", " ".join(classes))

    # Apply row/column commands
    _apply_commands(root, styleinfo, structure, layout_strategy=layout_strategy)

    # Pretty print
    if pretty_print:
        indent(root)

    if return_tree:
        return (root, structure, section_nodes)
    else:
        return _html_extract(root)

def _html_extract(root):
    if len(root) == 0 and root.text is None and root.tail is None:
        return ''
    return ET.tostring(root).replace('<html>','').replace('</html>','')

def _strip_presentation(tree):
    cleanup(tree, lambda t: t.tag == 'div')


def _sanitise_styleinfo(styleinfo, sect_ids):
    # Replace lists with sets
    out = {}
    for k, v in styleinfo.items():
        out[k] = set(v)

    # Ensure that all sections have an entry in styleinfo
    for sect_id in sect_ids:
        if not sect_id in out:
            out[sect_id] = set()

    return out

def _assert_sane_sections(root, structure):
    # First, all h1, h2 etc tags will be children of the root.
    # remove_tag should have ensured that, otherwise we will be unable
    # to cut the HTML into sections.
    for si in structure:
        parent = get_parent(root, si.node)
        if si.tag.lower() in headingdef and parent is not root:
            raise BadStructure("Section heading \"%(name)s\" is not at the top level of "
                               "the document. This interferes with the ability to "
                               "format the sections and apply columns. "
                               "Please move the heading out of the '%(element)s'"
                               " element that contains it." % dict(name=si.name, element=parent.tag.upper()))

def _apply_commands(root, styleinfo, structure, layout_strategy=None):
    # Rules:
    #  - No nesting of columns within columns
    #  - Within a given row, newcolumn must be applied to
    #    divs that are at the same level.
    #  - No columns allowed if newrow has not been started.

    # dict from node -> sect_id
    known_nodes = dict((si.node, si.sect_id) for si in structure)

    # Preprocess:
    #  - insert 'newcolumn' on everything that has 'newrow'
    for si in structure:
        if NEWROW in styleinfo[si.sect_id]:
            styleinfo[si.sect_id].add(NEWCOL)

    _add_rows_and_columns(root, known_nodes, styleinfo, layout_strategy=layout_strategy)
    # Due to HTML/CSS quirks, we add an empty <div
    # class="rowclear"> after every <div class="row">
    for n in root.getiterator():
        if n.tag == 'div' and layout_strategy.is_row_class(_get_classes_for_node(n)):
            rowclear = layout_strategy.row_end_html()
            if rowclear:
                elem = ET.fromstring(rowclear)
                n.append(elem)

def _find_child_with_column_structure(node, known_nodes, styleinfo):
    for n in node.getiterator():
        if n == node:
            continue # ignore root
        sect_id = known_nodes.get(n)
        if sect_id is not None:
            commands = styleinfo[sect_id]
            if NEWROW in commands or NEWCOL in commands:
                return (sect_id, n)
    return None

def _get_next_section_node(nodelist, known_nodes):
    for n in nodelist:
        sect_id = known_nodes.get(n)
        if sect_id is not None:
            return sect_id
    return None

# TODO - many of assumptions made in this function are now wrong, and requirements
# have changed, this is in major flux

def _add_rows_and_columns(topnode, known_nodes, styleinfo, layout_strategy=None):
    # This is the most involved and tricky part.  See the comments
    # above the 'format_html' function.

    # NB: known_nodes, and all nodes passed around and manipulated,
    # are the nodes of the containing divs we have added to the
    # document structure.

    cur_row_start = None
    children = list(topnode.getchildren()) # our own copy, which we don't change
    # Offset used to cope with the fact that we are pulling sub-nodes
    # out of topnode as we go along.
    idx_offset = 0
    for idx, node in enumerate(children):
        sect_id = known_nodes.get(node)
        if sect_id is None:
            # If not a section node, it cannot contain sections.
            # or have commands
            continue
        commands = styleinfo[sect_id]

        if NEWROW in commands:
            if cur_row_start is not None:
                # The previous row is finished
                _apply_row_col_divs(topnode, cur_row_start_idx + idx_offset, idx + idx_offset, columns, layout_strategy=layout_strategy)
                # We have removed (idx - cur_row_start_idx) elements,
                # and added one back
                idx_offset += -(idx - cur_row_start_idx) + 1
            # start a new row
            cur_row_start = node
            cur_row_start_idx = idx
            columns = []

        if NEWCOL in commands:
            if cur_row_start is None:
                # TODO - need name, not sect_id
                raise BadStructure("'New column' command was found on section "
                                   "'%(name)s' without an appropriate 'new row' "
                                   "command before it. " % dict(name=sect_id))
            else:
                columns.append((idx + idx_offset, sect_id))

        if cur_row_start:
            # Rows/columns can only be added within the same level of
            # nesting of the HTML document.  This means we do not need
            # to recurse if we have started adding rows/columns.

            # However, if we are actually in a '1 column row', we
            # allow a nested column structure, but only by imposing
            # constraints on what follows.
            child = _find_child_with_column_structure(node, known_nodes, styleinfo)
            if child is not None:
                if len(columns) > 1:
                    # Can't do it.
                    csect_id, cnode = child
                    # TODO - names not sect_ids
                    raise BadStructure("A '%(tag)s' item has a 'New row' or 'New column' command applied to "
                                       "it, but it is a subsection of '%(ptag)s: %(pname)s' which is already in a column. "
                                       "This would create a nested column structure, which is not allowed." %
                                       dict(tag=cnode[0].tag.upper(), ptag=cur_row_start[0].tag.upper(), pname=sect_id))
                else:
                    # Allow it, but next section on this level must
                    # not be NEWCOL (unless it is also NEWROW)
                    nextnode_sect_id = _get_next_section_node(children[idx+1:], known_nodes)
                    if nextnode_sect_id is not None:
                        nextnode_commands = styleinfo[nextnode_sect_id]
                        if NEWCOL in nextnode_commands and (NEWROW not in nextnode_commands):
                            # TODO - need name not sect_id
                            raise BadStructure("Item '%(ptag)s: %(pname)s' has a column structure within it "
                                               "but section '%(name)s' has a 'New column' command applied to "
                                               "it.  This would create a nested column structure, which is "
                                               "not allowed." % (dict(name=nextnode_sect_id, ptag=cur_row_start[0].tag.upper(), pname=sect_id)))
                    _add_rows_and_columns(node, known_nodes, styleinfo, layout_strategy=layout_strategy)

        else:
            _add_rows_and_columns(node, known_nodes, styleinfo, layout_strategy=layout_strategy)

        # If we are at last node, and are still in a row, there won't
        # be a NEWROW command, so we have to close implicitly,
        # including the current node in the row (hence idx + 1).
        if idx == len(children) - 1 and cur_row_start is not None \
                and len(columns) > 0:
                _apply_row_col_divs(topnode, cur_row_start_idx + idx_offset, idx + 1 + idx_offset, columns, layout_strategy=layout_strategy)


def _apply_row_col_divs(parent, start_idx, stop_idx, columns, layout_strategy):
    # Add the row
    total_columns = len(columns)
    newrow = wrap_elements_in_tag(parent, start_idx, stop_idx, 'div')
    newrow.set('class', ' '.join(layout_strategy.row_classes(total_columns)))

    # Add the columns
    if total_columns > MAXCOLS:
        # TODO need name not sect_id
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
        newcol.set('class', ' '.join(layout_strategy.column_classes(total_columns - i + 1, total_columns)))

def preview_html(html, pres):
    root, structure, section_nodes = format_html(html, pres, return_tree=True)
    known_nodes = _invert_dict(section_nodes)
    _create_preview(root, structure, known_nodes)
    return _html_extract(root)

def _replace_with_text(n, text):
    n[:] = []
    n.tail = ""
    n.text = text

def _create_preview(node, structure, known_nodes):
    for n in node.getchildren():
        if n.tag == 'div':
            _create_preview(n, structure, known_nodes)
        else:
            parent = node
            # TODO - need to get the name, known_nodes uses sect_id as value
            name = known_nodes.get(parent)
            if name is not None and (n.tag in blockdef):
                n.set('class', 'structural ' + "tag" + n.tag.lower() )
                n.tag = "div"
                n[:] = []
                n.text = name
            else:
                node.remove(n)

def extract_presentation(html):
    """
    Takes HTML with formatting applied and returns presentation elements (a
    dictionary with keys = section names, values = set of classes/commands) and
    the HTML without formatting (ready to be used in an editor)
    """
    # TODO: this function is not brilliantly well defined e.g.  should
    # there be an entry in the dictionary for sections with no
    # formatting?  This does not affect functionality, but it does
    # affect tests.
    layout_strategy = get_layout_details_strategy()
    root = parse(html)
    structure = get_structure(root)
    pres = {}
    for si in structure:
        pres[si.sect_id] = set()

        # Section - extract classes
        for c in _get_classes_for_node(si.node):
            pres[si.sect_id].add(PresentationClass(c))
            if 'class' in si.node.attrib:
                del si.node.attrib['class']

        # Add custom ids
        si.node.set('id', si.sect_id)

        # Parent/grandparent of section - newcol/newrow
        p = get_parent(root, si.node)
        if p is not None and p.tag == 'div':
            # We only care if si.node is the first child of the div
            if get_index(p, si.node) == 0:
                classes = _get_classes_for_node(p)
                if layout_strategy.is_column_class(classes):
                    pres[si.sect_id].add(NEWCOL)
                gp = get_parent(root, p)
                if gp is not None and gp.tag == 'div':
                    if layout_strategy.is_row_class(_get_classes_for_node(gp)) \
                            and get_index(gp, p) == 0:
                        pres[si.sect_id].add(NEWROW)
                        pres[si.sect_id].discard(NEWCOL) # for tidiness, not technically necessary

    _strip_presentation(root)
    out_html = _html_extract(root)

    return (pres, out_html)
