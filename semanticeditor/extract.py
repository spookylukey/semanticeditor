"""
Extract simple HTML and presentation info from combined HTML
"""

from semanticeditor.common import parse, get_structure, get_classes_for_node, html_extract, strip_presentation
from semanticeditor.definitions import PresentationClass, NEWROW, NEWCOL, NEWINNERROW, NEWINNERCOL
from semanticeditor.layout import get_layout_details_strategy
from semanticeditor.utils.etree import get_parent, get_index
from semanticeditor.utils.general import any


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
        for c in get_classes_for_node(si.node):
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

        # To know whether it is new/row col or *inner* row/col, we count the
        # number of levels of row divs.
        count_row_divs = _count_row_divs(root, si.node, layout_strategy)

        # New row
        if row_node is not None:
            if count_row_divs > 1:
                command = NEWINNERROW
            else:
                command = NEWROW

            r_classes = get_classes_for_node(row_node)
            row_pres = set([command] + [PresentationClass(c) for c in r_classes if not layout_strategy.is_row_class(c)])
            pres[command.prefix + si.sect_id] = row_pres

        # New column
        if col_node is not None:
            if count_row_divs > 1:
                command = NEWINNERCOL
            else:
                command = NEWCOL

            c_classes = get_classes_for_node(col_node)
            if inner_col_node is not None:
                c_classes.extend(get_classes_for_node(inner_col_node))
            col_pres = set([command] + [PresentationClass(c) for c in c_classes if not layout_strategy.is_column_class(c)])
            pres[command.prefix + si.sect_id] = col_pres

    strip_presentation(root)
    out_html = html_extract(root)

    return (pres, out_html)


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
        c_classes = get_classes_for_node(p)
        p_is_col = any(layout_strategy.is_column_class(c) for c in c_classes)

        gp = get_parent(root, p)
        if gp is not None and gp.tag == 'div' and get_index(gp, p) == 0:
            # We only locate row divs if col is first col within row
            r_classes = get_classes_for_node(gp)
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


def _count_row_divs(root, node, layout_strategy):
    """
    Counts the number of divs from root to node that are divs for layout rows
    """
    # Get the path from root to node.
    # This algorithmically bad, but probably fast enough.

    count = 0
    p = node
    while p is not root:
        p = get_parent(root, p)
        p_classes = get_classes_for_node(p)
        if any(layout_strategy.is_row_class(c) for c in p_classes):
            count += 1

    return count
