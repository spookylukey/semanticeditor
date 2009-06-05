"""
Utilities for manipulating the content provided by the user.
"""

from elementtree import ElementTree as ET
from semanticeditor.utils.etree import cleanup, flatten, get_parent, get_depth, get_index, wrap_elements_in_tag, indent
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

# The number of chars we trim block level elements to.
BLOCK_LEVEL_TRIM_LENGTH = 20

### Layout CSS class names ###

# This is designed to be user supply-able if necessary

class LayoutDetails(object):
    """
    Strategy object used for defining the details of CSS/HTML
    to be used when rendering a Layout.
    """
    ROW_CLASS = "row"
    COLUMN_CLASS = "column"

    # Public interface:
    max_columns = 4
    def row_classes(self, column_count):
        """
        Returns a list of CSS classes to be used for a row containing
        column_count columns
        """
        retval = [self.ROW_CLASS]
        if column_count > 1:
            retval.append("columns%d" % column_count)
        return retval

    def column_classes(self, column_num, column_count):
        """
        Returns a list of CSS classes to be used for a column which is number
        column_num out of column_count.
        """
        if column_count == 1:
            # No classes
            return []
        retval = [self.COLUMN_CLASS]
        if column_num == 1:
            retval.append("firstcolumn")
        if column_num == column_count:
            retval.append("lastcolumn")
        return retval

    def is_row_class(self, class_):
        """
        Returns true if the class (a string) corresponds
        to a CSS class used for a row.
        """
        return class_ == self.ROW_CLASS or re.match(r'^columns\d+$', class_)

    def is_column_class(self, class_):
        """
        Returns true if the class (a string) corresponds
        to a CSS class used for a column.
        """
        return class_ == self.COLUMN_CLASS or re.match(r'^(first|last)column$', class_)

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
            # Section id - use existing if it is their, but don't duplicate
            sect_id = n.get('id', '')
            if sect_id == '' or not sect_id.startswith(n.tag) or sect_id in sect_ids:
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
                names.add(name)

                # Paragraphs etc within a section should be indented
                # one further than the heading above them.
                if len(heading_names) == 0:
                    level = 1
                else:
                    level = cur_level + 1

            # Level is adjusted so that e.g. H3 is level 1, if it is
            # the first to appear in the document.
            # It is also adjusted so that nested items (e.g. p in blockquote)
            # appear to be nested.
            nesting_level = get_depth(root, n) - 1
            retval.append(StructureItem(level=nesting_level + level - first_heading_level + 1,
                                        sect_id=sect_id,
                                        name=name,
                                        tag=n.tag.upper(),
                                        node=n))

    return retval

def _get_classes_from_presinfo(presinfos):
    # Extract a list of classes from a list of PresentationInfo objects
    return [pi.name for pi in presinfos if pi.prestype == "class"]

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

def format_html(html, styleinfo, return_tree=False, pretty_print=False):
    """
    Formats the XHTML given using a dictionary of style information.
    The dictionary has keys which are the ids of sections,
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

    # Apply normal CSS classes.
    for si in structure:
        # Apply css styles
        classes = _get_classes_from_presinfo(styleinfo[si.sect_id])
        classes.sort()
        if classes:
            si.node.set("class", " ".join(classes))

    # Create layout from row/column commands
    layout = _create_layout(root, styleinfo, structure)
    _check_layout(layout, structure, layout_strategy)
    # Create new ET tree from layout.  The individual nodes that belong to
    # 'root' are not altered, but just added to a new tree.  This means that the
    # information in 'structure' does not need updating.
    rendered = _render_layout(layout, layout_strategy)

    # Pretty print
    if pretty_print:
        indent(rendered)

    # Remove the temporary IDs we may have added when splitting the HTML
    # into content and presentation.  We don't do this before this point,
    # as the IDs need to be there to identify sections
    for si in structure:
        if 'id' in si.node.attrib:
            del si.node.attrib['id']

    if return_tree:
        return (rendered, structure, section_nodes)
    else:
        return _html_extract(rendered)

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

#### Layout related ####

Layout = struct("Layout", (object,), dict(rows=list))
LayoutRow = struct("LayoutRow", (object,), dict(columns=list, styles=list))
LayoutColumn = struct("LayoutColumn", (object,), dict(nodes=list, styles=list))

_NEWROW_PREFIX = 'newrow_'
_NEWCOL_PREFIX = 'newcol_'

def _find_layout_commands(root, structure, styleinfo):
    # Layout commands are not stored against normal sections,
    # but have their own entry in the section list, using an id
    # of 'newrow_' or 'newcol_' + id of block they preceed.

    sect_dict = dict((s.sect_id, s) for s in structure)
    row_info = {} # key = sect_id, val = [PresentationInfo]
    col_info = {} # key = sect_id, val = [PresentationInfo]
    for sect_id, presinfo in styleinfo.items():
        if sect_id.startswith(_NEWROW_PREFIX):
            real_sect_id = sect_id[len(_NEWROW_PREFIX):]
            sect = sect_dict.get(real_sect_id)
            if sect is not None:
                parent = get_parent(root, sect.node)
                if parent is not root:
                    raise BadStructure("Section \"%(name)s\" is not at the top level of "
                                       "the document, and therefore cannot have a column "
                                       "structure applied to it.  Please move the 'New row' "
                                       "command to a top level element." %
                                       dict(name=sect.name))

                row_info[real_sect_id] = presinfo

        if sect_id.startswith(_NEWCOL_PREFIX):
            real_sect_id = sect_id[len(_NEWCOL_PREFIX):]
            sect = sect_dict.get(real_sect_id)
            if sect is not None:
                parent = get_parent(root, sect.node)
                if parent is not root:
                    raise BadStructure("Section \"%(name)s\" is not at the top level of "
                                       "the document, and therefore cannot have a column "
                                       "structure applied to it.  Please move the 'New column' "
                                       "command to a top level element." %
                                       dict(name=sect.name))
                col_info[real_sect_id] = presinfo

    return row_info, col_info

def _create_layout(root, styleinfo, structure):
    # Find the layout commands
    row_info, col_info = _find_layout_commands(root, structure, styleinfo)

    # Build a Layout structure

    # We put everything inside a Row and Column, even if there is
    # only one column.
    layout = Layout()
    row = LayoutRow()
    col = LayoutColumn()
    sect_dict = dict((si.node, si) for si in structure)

    # Build Layout
    for node in root.getchildren():
        si = sect_dict.get(node)

        if si:
           row_presinfo = row_info.get(si.sect_id)
           if row_presinfo is not None:
               # We can assume row_presinfo contains NEWROW command

               # Finish current col and row, if they have anything in them
               if col.nodes:
                   row.columns.append(col)
               if row.columns:
                   layout.rows.append(row)
               # Start new row with styles
               row = LayoutRow(styles=_get_classes_from_presinfo(row_presinfo))
               # Start new col
               col = LayoutColumn()

           col_presinfo = col_info.get(si.sect_id)
           if col_presinfo is not None:
               # Assume col_presinfo contains NEWCOL command

               # Finish current col, if it is non-empty
               if col.nodes:
                   row.columns.append(col)
               # Start new col with styles
               col = LayoutColumn(styles=_get_classes_from_presinfo(col_presinfo))

        # Now deal with content itself
        col.nodes.append(node)

    # Close last col and row
    if col.nodes:
        row.columns.append(col)
    layout.rows.append(row)

    return layout

def _check_layout(layout, structure, layout_strategy):
    sect_dict = dict((si.node, si) for si in structure)
    max_cols = layout_strategy.max_columns
    for row in layout.rows:
        if len(row.columns) > max_cols:
            # Look at first node in first bad column
            node = row.columns[max_cols - 1].nodes[0]
            sect = sect_dict[node]
            raise TooManyColumns("The maximum number of columns is %(max)d. "
                                 "Please move section '%(name)s' into a new "
                                 "row." % dict(max=max_cols, name=sect.name))

def _render_layout(layout, layout_strategy):
    root = ET.fromstring("<html></html>")
    for row in layout.rows:
        column_count = len(row.columns)
        rowdiv = ET.Element('div')
        classes = layout_strategy.row_classes(column_count) + row.styles
        if classes:
            rowdiv.set('class', ' '.join(classes))
        for i, col in  enumerate(row.columns):
            coldiv = ET.Element('div')
            classes = layout_strategy.column_classes(i + 1, column_count) + col.styles
            if classes:
                coldiv.set('class', ' '.join(classes))
            for n in col.nodes:
                coldiv.append(n)
            rowdiv.append(coldiv)
        root.append(rowdiv)
    return root

def preview_html(html, pres):
    root, structure, section_nodes = format_html(html, pres, return_tree=True)
    known_nodes = _invert_dict(section_nodes)
    _create_preview(root, structure, known_nodes)
    return _html_extract(root)

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

        # Add custom ids.  These are only for purpose of editing,
        # and will be removed again at end of format_html
        si.node.set('id', si.sect_id)

        # Parent/grandparent of section - newcol/newrow
        p = get_parent(root, si.node)
        if p is not None and p.tag == 'div' and (get_index(p, si.node) == 0):
            # We only care if si.node is the first child of the column div
            gp = get_parent(root, p)
            if gp is not None and gp.tag == 'div':
                # We can't always tell if something is a row/col, but hopefully
                # we can identify one, which will tell us we are in a column
                # structure.
                r_classes = _get_classes_for_node(gp)
                c_classes = _get_classes_for_node(p)
                gp_is_row = any(layout_strategy.is_row_class(c) for c in r_classes)
                p_is_col = any(layout_strategy.is_column_class(c) for c in c_classes)

                if gp_is_row or p_is_col:
                    # New column
                    col_pres = set([NEWCOL] + [PresentationClass(c) for c in c_classes if not layout_strategy.is_column_class(c)])
                    pres[_NEWCOL_PREFIX + si.sect_id] = col_pres
                    if get_index(gp, p) == 0:
                       # first column, therefore new row
                       row_pres = set([NEWROW] + [PresentationClass(c) for c in r_classes if not layout_strategy.is_row_class(c)])
                       pres[_NEWROW_PREFIX + si.sect_id] = row_pres


    _strip_presentation(root)
    out_html = _html_extract(root)

    return (pres, out_html)
