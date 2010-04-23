"""
Utilities for manipulating the content provided by the user.
"""

from lxml import etree as ET
from lxml.html import HTMLParser
from pyquery import PyQuery as pq
from semanticeditor.utils.etree import cleanup, flatten, get_parent, get_depth, get_index, indent, eliminate_tag
from semanticeditor.utils.datastructures import struct
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

technical_blockdef = set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ol', 'ul', 'blockquote']) # according to HTML4
additional_blockdef = set(['li']) # li really act like block elements
blockdef = technical_blockdef | additional_blockdef
blockdef_selector = ",".join(blockdef) # need to sync with wymeditor.semantic.js
headingdef = set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
preview_blockdef = technical_blockdef

# The number of chars we trim block level elements to.
BLOCK_LEVEL_TRIM_LENGTH = 200

### Layout CSS class names ###

# This is designed to be user supply-able if necessary

class LayoutDetailsBase(object):
    """
    Base class for strategy object used to define the details of
    CSS/HTML to be used when rendering a layout
    """
    # Inherit from this class if creating your own custom class.  LayoutDetails
    # provides a concrete implementation.

    def _raise_not_implemented(self):
        raise NotImplementedError()

    max_columns = property(_raise_not_implemented, doc="""Maximum number of columns to allow""")

    use_inner_column_div = property(_raise_not_implemented, doc="""True to wrap all column content in a inner div""")

    def row_classes(self, logical_column_count, actual_column_count):
        """
        Returns a list of CSS classes to be used for a row containing
        logical_column_count 'logical' columns, actual_column_count 'actual'
        columns.  'actual' columns are present in the HTML structure, but some
        might be, for example, double width, so are counted as two logical
        columns.
        """
        raise NotImplementedError()

    def column_classes(self, logical_column_num, actual_column_num, logical_column_count, actual_column_count):
        """
        Returns a list of CSS classes to be used for a column which is number
        column_num out of column_count.  (see above regarding logical/actual)
        """
        raise NotImplementedError()

    def is_row_class(self, class_):
        """
        Returns true if the class (a string) corresponds to a CSS class used for
        a row.
        """
        raise NotImplementedError

    def is_column_class(self, class_):
        """
        Returns true if the class (a string) corresponds to a CSS class used for
        a column.
        """
        raise NotImplementedError()

    def row_end_html(self):
        """
        Returns some raw HTML to be added at the end of a row (e.g. for clearing
        floats) if necessary.
        """
        return ""

    def outer_column_classes(self, presinfo):
        """
        Given a list a PresentationInfo objects, return the ones that should be
        applied to the outer column div.
        """
        if not self.use_inner_column_div:
            return presinfo
        else:
            raise NotImplementedError()

    def inner_column_classes(self, presinfo):
        """
        Given a list a PresentationInfo objects, return the ones that should be
        applied to the inner column div.  (Never called if use_inner_column_div
        = False)
        """
        raise NotImplementedError()

    # Hacks, optional
    def format_pre_parse_hacks(self, html, styleinfo):
        """
        For formatting, applies hacks to unformatted HTML before parsing,
        returns HTML to be used.
        """
        return html

    def format_post_parse_hacks(self, tree, styleinfo):
        """
        For formatting, applies hacks to tree after parsing, returns new tree to
        be used.
        """
        return tree

    def format_structure_hacks(self, structure, styleinfo):
        """
        For formatting, given a list of StructureItems and a list of
        PresentationInfos, applies hacks and returns new structure to be used.
        """
        return structure

    def format_post_layout_hacks(self, tree, structure, styleinfo):
        """
        For formatting, given the tree after layout, the structure and style
        info, apply hacks and return a new tree.
        """
        return tree

    def extract_pre_parse_hacks(self, html):
        """
        For extracting presentation info, applies hacks to formatted HTML before
        parsing, and returns HTML to be used.
        """
        return html

    def extract_post_parse_hacks(self, tree):
        """
        For extracting presentation info, applies hacks to parse tree before
        after parsing, and returns tree.
        """
        return tree

    def extract_structure_hacks(self, structure):
        """
        For extracting presentation info, given a list of StructureItems,
        applies hacks and returns new structure to be used.
        """
        return structure

class LayoutDetails(LayoutDetailsBase):
    """
    Strategy object used for defining the details of CSS/HTML to be used when
    rendering a Layout.  This is a concrete implementation.
    """
    ROW_CLASS = "row"
    COLUMN_CLASS = "column"

    max_columns = 6

    use_inner_column_div = True

    def row_classes(self, logical_column_count, actual_column_count):
        retval = [self.ROW_CLASS]
        if actual_column_count > 1:
            retval.append("columns%d" % logical_column_count)
        return retval

    def column_classes(self, logical_column_num, actual_column_num, logical_column_count, actual_column_count):
        if actual_column_count == 1:
            # No classes
            return []
        retval = [self.COLUMN_CLASS]
        if actual_column_num == 1:
            retval.append("firstcolumn")
        if actual_column_num == actual_column_count:
            retval.append("lastcolumn")
        return retval

    def is_row_class(self, class_):
        return class_ == self.ROW_CLASS or re.match(r'^columns\d+$', class_)

    def is_column_class(self, class_):
        return class_ == self.COLUMN_CLASS or re.match(r'^(first|last)column$', class_)

    def row_end_html(self):
        return ""

    def outer_column_classes(self, presinfo):
        return [pi for pi in presinfo if pi.column_equiv is not None]

    def inner_column_classes(self, presinfo):
        return [pi for pi in presinfo if pi.column_equiv is None]

    # Hacks
    def format_post_layout_hacks(self, tree, structure, styleinfo):
        # WYMEditor cannot insert divs. This is a workaround
        for n in tree.getiterator():
            if n.tag == 'p' and ('div' in _get_classes_for_node(n)):
                n.tag = 'div'
            if n.tag == 'p':
                # If only child element is a plugin object, convert to
                # a div.
                # NB: current implementation of plugin objects is that they
                # are represented by an image in the editor.  Our code has to
                # run before these are converted, so we have to work with this
                # implementation detail.
                children = n.getchildren()
                if ((n.text is None or n.text.strip() == "")
                    and len(children) == 1
                    and children[0].tag == "img"
                    and (children[0].tail is None or children[0].tail.strip() == "")
                    and children[0].attrib.get('id', '').startswith("plugin_obj")):
                        n.tag = 'div'
                        # Add 'div' to list of classes
                        # This handles the reverse transform for us:
                        n.attrib['class'] = ' '.join(n.attrib.get('class', '').split(' ') + ['div']).strip()
        return tree

    def extract_post_parse_hacks(self, tree):
        # inverse part of above workaround
        for n in tree.getiterator():
            if n.tag == 'div' and ('div' in _get_classes_for_node(n)):
                n.tag = 'p'
        return tree

### Parsing ###
def parse(content, clean=False):
    """
    Parses the HTML provided into an ElementTree.
    If 'clean' is True, lax parsing is done, the tree is cleaned
    of dirty user provided HTML
    """
    # We also use HTMLParser for 'strict', because the XML parser seems to eliminate
    # '\r' for some reason.
    tree = ET.fromstring(u'<html><body>' + content + u'</body></html>', parser=HTMLParser())
    if clean:
        clean_tree(tree)
    return tree

# NB: ElementTree is bizarre - after parsing some UTF-8 bytestrings, it will
# then return nodes that are 'str's if the text is all ASCII, otherwise
# 'unicode's (having correctly interpreted the UTF-8).  When serialising to
# JSON, this works out OK actually, so we leave it as is for the moment.

def pretty_print(content):
    t = parse(content)
    indent(t)
    return _html_extract(t)

### Semantic editor functionality ###

## Presentation dictionary utilities

class PresentationInfo(object):
    """
    Encapsulates a piece of presentation information.
    """
    def __init__(self, prestype=None, name=None, verbose_name="", description="", allowed_elements=None, column_equiv=None):
        self.prestype = prestype
        self.name = name
        # verbose_name, description and allowed_elements are additional pieces
        # of information that are only needed when the client is requesting a
        # list of styles.  In other sitations these objects may not have these
        # attributes filled in.
        self.verbose_name = verbose_name
        self.description = description
        if allowed_elements is None:
            allowed_elements = []
        self.allowed_elements = allowed_elements
        self.column_equiv = column_equiv

    def __eq__(self, other):
        return self.prestype == other.prestype and self.name == other.name

    def __hash__(self):
        return hash(self.prestype) ^ hash(self.name)

    def __repr__(self):
        return "PresentationInfo(prestype=\"%s\", name=\"%s\")" % (self.prestype, self.name)

def PresentationClass(name, verbose_name="", description="", allowed_elements=None, column_equiv=None):
    """
    Shortcut for creating CSS classes
    """
    return PresentationInfo(prestype="class", name=name,
                            verbose_name=verbose_name, description=description,
                            allowed_elements=allowed_elements,
                            column_equiv=column_equiv)

def PresentationCommand(name, verbose_name="", description=""):
    """
    Shortcut for creating commands
    """
    return PresentationInfo(prestype="command", name=name,
                            verbose_name=verbose_name, description=description,
                            allowed_elements=sorted(list(technical_blockdef)))

NEWROW = PresentationCommand('newrow',
                             verbose_name="New row",
                             description="""
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

"""
                             )

NEWCOL = PresentationCommand('newcol',
                             verbose_name="New column",
                             description="""
<p>Use this command to start a new column, after a 'New row'
command has been used to start a set of columns.</p>

""")

COMMANDS = [NEWROW, NEWCOL]

## General utilities

def any(seq):
    for i in seq:
        if i:
            return True
    return False

def _invert_dict(d):
    return dict((v, k) for (k, v) in d.items())

def _get_classes_for_node(node):
    return filter(len, node.get('class', '').split(' '))

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


### Structure related ###

class StructureItem(object):
    __metaclass__ = struct
    level = 0     #    level is the 'outline level' in the document i.e. an integer
    sect_id = ''  #    sect_id is a unique ID used for storing presentation information against
    name = ''     #    name is a user presentable name for the section
    tag = ''      #    tag is the HTML element e.g. h1
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

    # Pre-pass to get existing ids.
    for n in root.getiterator():
        if n.tag in blockdef:
            sect_id = n.get('id')
            if sect_id is not None:
                if not sect_id.startswith(n.tag) or sect_id in sect_ids:
                    # don't use invalid or duplicate ids.
                    # remove
                    del n.attrib['id']
                else:
                    # reserve
                    sect_ids.add(sect_id)

    for n in root.getiterator():
        if n.tag in blockdef:
            text = flatten(n)
            sect_id = n.get('id')
            if sect_id is None:
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
                                                dict(name=name, foundnum=level,
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
            nesting_level = get_depth(root, n) - 2
            retval.append(StructureItem(level=nesting_level + level - first_heading_level + 1,
                                        sect_id=sect_id,
                                        name=name,
                                        tag=n.tag.lower(),
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
    # This function is no longer used externally, but it has tests
    # against it that are useful at checking the behaviour of get_structure
    tree = parse(content, clean=True)
    structure = get_structure(tree, assert_structure=True)
    return structure

def format_html(html, styleinfo, return_tree=False, pretty_print=False):
    """
    Formats the XHTML given using a dictionary of style information.
    The dictionary has keys which are the ids of sections,
    and values which are lists of CSS classes or special commands.
    """
    layout_strategy = get_layout_details_strategy()
    html = layout_strategy.format_pre_parse_hacks(html, styleinfo)
    root = parse(html, clean=True)
    root = layout_strategy.format_post_parse_hacks(root, styleinfo)
    structure = get_structure(root, assert_structure=True)
    structure = layout_strategy.format_structure_hacks(structure, styleinfo)
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
    rendered = layout_strategy.format_post_layout_hacks(rendered, structure, styleinfo)

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
        return (rendered, structure)
    else:
        return _html_extract(rendered)

def _html_extract(root):
    if len(root) == 0 and root.text is None and root.tail is None:
        return ''
    return ET.tostring(root).replace('<html>', '').replace('</html>', '').replace('<body>', '').replace('</body>', '').replace("<head/>", "").replace("&#13;", "\r")

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

# Some dumb container structures
Layout = struct("Layout", (object,), dict(rows=list))
LayoutRow = struct("LayoutRow", (object,), dict(columns=list, presinfo=list))
LayoutColumn = struct("LayoutColumn", (object,), dict(nodes=list, presinfo=list))

_NEWROW_PREFIX = 'newrow_'
_NEWCOL_PREFIX = 'newcol_'

def _layout_column_width(col):
    """
    Returns the logical column width of a column
    """
    column_equivs = [pi.column_equiv for pi in col.presinfo if pi.column_equiv is not None]
    if len(column_equivs) > 0:
        # assume user has not done something silly like put
        # *2* column_equiv classes on a column
        return column_equivs[0]
    else:
        return 1

def _layout_column_count(row):
    """
    Get the number of logical columns in a LayoutRow
    """
    return sum(_layout_column_width(c) for c in row.columns)

def is_root(node):
    return node.tag == 'html' or node.tag == 'body'

def _find_layout_commands(root, structure, styleinfo):
    # Layout commands are not stored against normal sections,
    # but have their own entry in the section list, using an id
    # of 'newrow_' or 'newcol_' + id of block they precede.

    sect_dict = dict((s.sect_id, s) for s in structure)
    row_info = {} # key = sect_id, val = [PresentationInfo]
    col_info = {} # key = sect_id, val = [PresentationInfo]
    for sect_id, presinfo in styleinfo.items():
        if sect_id.startswith(_NEWROW_PREFIX):
            real_sect_id = sect_id[len(_NEWROW_PREFIX):]
            sect = sect_dict.get(real_sect_id)
            if sect is not None:
                parent = get_parent(root, sect.node)
                if not is_root(parent):
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
                if not is_root(parent):
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
    children = root.getchildren()
    if children and children[0].tag == 'body':
        children = children[0].getchildren()

    for node in children:
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
                row = LayoutRow(presinfo=row_presinfo)
                # Start new col
                col = LayoutColumn()

            col_presinfo = col_info.get(si.sect_id)
            if col_presinfo is not None:
                # Assume col_presinfo contains NEWCOL command

                # Finish current col, if it is non-empty
                if col.nodes:
                    row.columns.append(col)
                # Start new col with styles
                col = LayoutColumn(presinfo=col_presinfo)

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
        if _layout_column_count(row) > max_cols:
            # Because columns can be multiple width, we can't easily work out
            # which column needs to be moved, so just refer user to whole
            # section.
            node = row.columns[0].nodes[0]
            sect = sect_dict[node]
            raise TooManyColumns("The maximum number of columns is %(max)d. "
                                 "Please adjust columns in section '%(name)s'." %
                                 dict(max=max_cols, name=sect.name))

def _render_layout(layout, layout_strategy):
    docroot = ET.fromstring("<html><body></body></html>")
    root = docroot.getchildren()[0] # body
    for row in layout.rows:
        # Row
        logical_column_count = _layout_column_count(row)
        actual_column_count = len(row.columns)
        rowdiv = ET.Element('div')
        classes = layout_strategy.row_classes(logical_column_count, actual_column_count) + _get_classes_from_presinfo(row.presinfo)
        if classes:
            rowdiv.set('class', ' '.join(classes))

        # Columns
        logical_column_num = 1
        for i, col in  enumerate(row.columns):
            coldiv = ET.Element('div')
            classes = layout_strategy.column_classes(logical_column_num,
                                                     i + 1,
                                                     logical_column_count,
                                                     actual_column_count) + \
                    _get_classes_from_presinfo(layout_strategy.outer_column_classes(col.presinfo))
            if classes:
                coldiv.set('class', ' '.join(classes))
            if layout_strategy.use_inner_column_div:
                contentdiv = ET.Element('div')
                coldiv.append(contentdiv)
                inner_classes = _get_classes_from_presinfo(layout_strategy.inner_column_classes(col.presinfo))
                if inner_classes:
                    contentdiv.set('class', ' '.join(inner_classes))
            else:
                contentdiv = coldiv
            for n in col.nodes:
                contentdiv.append(n)
            rowdiv.append(coldiv)

            logical_column_num += _layout_column_width(col)
        root.append(rowdiv)
    return docroot

def preview_html(html, pres):
    root, structure = format_html(html, pres, return_tree=True)
    structure2 = [si for si in structure if si.tag in preview_blockdef]
    known_nodes = dict((si.node, si) for si in structure2)
    _create_preview(root, structure2, known_nodes)
    return _html_extract(root)

def _create_preview(node, structure, known_nodes):
    children = node.getchildren()
    if children and children[0].tag == 'body':
        children = children[0].getchildren()
    for n in children:
        if n.tag == 'div':
            _create_preview(n, structure, known_nodes)
        else:
            sect = known_nodes.get(n)
            if sect is not None and (n.tag in blockdef):
                n.set('class', 'structural ' + "tag" + n.tag.lower())
                n.tag = "div"
                n[:] = []
                n.text = sect.name
            else:
                node.remove(n)

def _find_row_col_divs(root, node, layout_strategy):
    """
    Finds the row and column divs that a node belongs to.
    Returns a 3 tuple (row_div, col_div, inner_col_div)

    col_div is None if the node is not the first content
    node within that column.

    row_div is None if the node is not the first content node
    within that row.

    inner_col_div is None if there is no inner column div,
    or if col_div is None
    """
    # Keep going up until we find a 'row' div or 'column' div
    # that are parent/child.

    p = get_parent(root, node)
    gp = None

    p_is_col, gp_is_row = False, False
    row_div, col_div, inner_col_div = None, None, None

    if p is not None and p.tag == 'div' and get_index(p, node) == 0:
        # We only care if node is the first child of the column div
        c_classes = _get_classes_for_node(p)
        p_is_col = any(layout_strategy.is_column_class(c) for c in c_classes)

        gp = get_parent(root, p)
        if gp is not None and gp.tag == 'div' and get_index(gp, p) == 0:
            # We only locate row divs if col is first col within row
            r_classes = _get_classes_for_node(gp)
            gp_is_row = any(layout_strategy.is_row_class(c) for c in r_classes)

            # We can't always tell if something is a col (especially for single
            # column structure), but by identfying the row we can tell we are in
            # a column structure.
            if gp_is_row:
                p_is_col = True

    if gp_is_row:
        row_div = gp
    if p_is_col:
        col_div = p

    if not p_is_col:
        if p is not None and p.tag == 'div' and get_index(p, node) == 0:
            # Try to go up one
            row_div, col_div, inner_col_div = _find_row_col_divs(root, p, layout_strategy)
            if inner_col_div is None and col_div is not None:
                # We now know that current parent 'p' is inner_col_div
                inner_col_div = p
            return (row_div, col_div, inner_col_div)

    return (row_div, col_div, inner_col_div)

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
    html = layout_strategy.extract_pre_parse_hacks(html)
    root = parse(html, clean=False) # it's important we don't clean.
    root = layout_strategy.extract_post_parse_hacks(root)
    structure = get_structure(root)
    structure = layout_strategy.extract_structure_hacks(structure)
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

        # Try to find 'row' and 'column' divs that this node belongs to.
        # Columns can have inner divs for styling purposes.  Some CSS classes
        # will be applied to the outer column div, some to the inner column div.

        row_node, col_node, inner_col_node = _find_row_col_divs(root, si.node, layout_strategy)

        if row_node is not None:
            r_classes = _get_classes_for_node(row_node)
            row_pres = set([NEWROW] + [PresentationClass(c) for c in r_classes if not layout_strategy.is_row_class(c)])
            pres[_NEWROW_PREFIX + si.sect_id] = row_pres

        if col_node is not None:
            c_classes = _get_classes_for_node(col_node)
            if inner_col_node is not None:
                c_classes.extend(_get_classes_for_node(inner_col_node))
            col_pres = set([NEWCOL] + [PresentationClass(c) for c in c_classes if not layout_strategy.is_column_class(c)])
            pres[_NEWCOL_PREFIX + si.sect_id] = col_pres

    _strip_presentation(root)
    out_html = _html_extract(root)

    return (pres, out_html)

def _clean_elem(d):
    for x in ['style', 'class']:
        try:
            d.removeAttr(x)
        except KeyError:
            pass

def _empty_text(x):
    return x is None or x.strip() == ""

def _promote_child_text(elem, tag):
    """
    Ensure any leading or trailing text directly as a child of elem is wrapped
    in a tag.
    """
    if not _empty_text(elem.text):
        newtag = ET.Element(tag)
        newtag.text = elem.text
        elem.insert(0, newtag)
        elem.text = None

    if len(elem) > 0 and not _empty_text(elem[-1].tail):
        newtag = ET.Element(tag)
        newtag.text = elem[-1].tail
        elem[-1].tail = None
        elem.append(newtag)

def _clean_nested(elem):
    for idx, child in reversed(list(enumerate(elem.getchildren()))):
        # (do it reversed so that indexes never change as we mutate children)
        _clean_nested(child)
        if child.tag == 'p' and elem.tag == 'p':
            eliminate_tag(elem, idx)

def _replace_block_elements(elem):
    for child in elem.getchildren():
        if child.tag == 'div':
            child.tag = 'p'
        _replace_block_elements(child)

def _remove_command_divs(elem):
    for child in reversed(elem.getchildren()):
        _remove_command_divs(child)
        if child.tag == 'div' or child.tag == 'p':
            classes = set(_get_classes_for_node(child))
            if any(c.name in classes for c in COMMANDS):
                elem.remove(child)

def clean_tree(root):
    """
    Cleans dirty HTML from an ElementTree
    """
    initial_html = _html_extract(root)
    body = root[0] # <html><body>
    # If there is text directly in body, it needs wrapping in a block element.
    _promote_child_text(body, 'p')

    # replace 'command' divs
    _remove_command_divs(body)

    # First replace divs
    _replace_block_elements(body)

    # Deal with nested 'p's and other elements.
    _clean_nested(body)

    doc = pq(root)
    doc('*').each(_clean_elem)
    doc('style').remove()
    doc('col').remove()

    def pull_up(n):
        p = get_parent(body, n)
        i = get_index(p, n)
        eliminate_tag(p, i)

    for x in ['table', 'tbody', 'thead', 'tr', 'td', 'span', 'li p:only-child']:
        for n in doc(x):
            pull_up(n)
    # "li p:only-child" appears to be buggy.  It works like
    # "li p:only-descendent" or something.

    for x in ['strong', 'em', 'b', 'i']:
        for n in doc(x):
            if pq(n).is_(blockdef_selector):
                pull_up(n)

    # remove duplicate 'id' attributes.
    ids = [n.get('id', None) for n in doc('*[id]')]
    ids = [i for i in ids if i != "" and i != None]
    for i in set(ids):
        for j, node in enumerate(doc('#' + i)):
            if (j > 0): # skip the first one
                del node.attrib['id']

    for x in ['p + br', 'p:empty']:
        doc(x).remove()

    # Removed elements can give problems which need to be fixed again.  We keep
    # iterating through this until we get the same answer!
    output_html = _html_extract(root)
    if initial_html == output_html:
        return
    else:
        clean_tree(root)

def clean_html(html):
    tree = parse(html, clean=True)
    return _html_extract(tree)
