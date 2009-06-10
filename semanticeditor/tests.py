# -*- coding: utf-8 -*-

from django.test import TestCase
from semanticeditor.utils import extract_structure, InvalidHtml, IncorrectHeadings, format_html, parse, get_parent, get_index, BadStructure, TooManyColumns, NEWROW, NEWCOL, extract_presentation, get_structure
from semanticeditor.utils.presentation import PresentationInfo, PresentationClass, StructureItem

PC = PresentationClass

class TestExtractStructure(TestCase):
    def test_extract_structure(self):
        self.assertEqual([(s.level, s.sect_id, s.name, s.tag) for s in extract_structure("""
<h1>Heading <b>with </b><i>embedded <em>stuff</em> in</i> it</h1> Hmm
<p>A long paragraph with some actual content</p>
<h2>A sub heading</h2>
<p>Another para</p>
<h3>level 3</h3>
<p>A long paragraph with some actual content</p>
<h4>level 4</h4>
<p>Another para</p>
<h5>level 5</h5>
<p>nasty  éééééééééééééééééééééééééé</p>
<h6>level 6</h6>
<h1>Heading two</h1>
""")],
        [(1, "h1_1", u"Heading with embedded stuff in it", u"H1"),
         (2, "p_1", u"A long paragraph wit...", u"P"),
         (2, "h2_1", u"A sub heading", u"H2"),
         (3, "p_2", u"Another para...", u"P"),
         (3, "h3_1", u"level 3", u"H3"),
         (4, "p_3", u"A long paragraph wit...2", u"P"),
         (4, "h4_1", u"level 4", u"H4"),
         (5, "p_4", u"Another para...2", u"P"),
         (5, "h5_1", u"level 5", u"H5"),
         (6, "p_5", u"nasty  ééééééééééééé...", u"P"),
         (6, "h6_1", u"level 6", u"H6"),
         (1, "h1_2", u"Heading two", u"H1"),
         ])

    def test_extract_structure_missing(self):
        self.assertEqual(extract_structure("Hello"), [])

    def test_rejects_bad_html(self):
        self.assertRaises(InvalidHtml, extract_structure, "<h1>Foo")

    def test_rejects_higher_headings_later(self):
        """
        Ensures that if the first heading is e.g. h2, no h1 headings
        are allowed
        """
        self.assertRaises(IncorrectHeadings, extract_structure, "<h2>Hello</h2><h1>Hi</h1>")

    def test_rejects_improper_headings(self):
        self.assertRaises(IncorrectHeadings, extract_structure, "<h1>Hello</h1><h3>Bad heading</h3>")

    def test_rejects_duplicate_headings(self):
        self.assertRaises(IncorrectHeadings, extract_structure, "<h1>Hello</h1><h2>Hello</h2>")

    def test_use_existing_sect_ids(self):
        html = "<h1 id='h1_10'>Hi</h1><h1>There</h1>"
        structure = get_structure(parse(html))
        self.assertEqual(structure[0].sect_id, "h1_10")
        self.assertEqual(structure[1].sect_id, "h1_1")

    def test_dont_use_duplicate_existing_sect_id(self):
        html = "<h1 id='h1_10'>Hi</h1><h1 id='h1_10'>There</h1>"
        structure = get_structure(parse(html))
        self.assertEqual(structure[0].sect_id, "h1_10")
        self.assertEqual(structure[1].sect_id, "h1_1")

    def test_regression_1(self):
        # A bug in using existing section ids
        html = '<h1 id="h1_1">heading 1</h1><h1>A new heading</h1><h1 id="h1_2">heading 2</h1><h1 id="h1_3">heading 3</h1>'
        structure = get_structure(parse(html))
        self.assertEqual(["h1_1", "h1_4", "h1_2", "h1_3"], [s.sect_id for s in structure])

class TestPresentationInfo(TestCase):
    def test_equality(self):
        p1 = PresentationInfo(prestype="command", name="foo", verbose_name="blah")
        p2 = PresentationInfo(prestype="command", name="foo")
        p3 = PresentationInfo(prestype="command", name="bar")
        self.assertEqual(p1, p2)
        self.assertNotEqual(p2, p3)
        self.assertEqual(set([p1]), set([p2]))

class TestFormat(TestCase):
    def test_empty(self):
        self.assertEqual('<div class="row" />', format_html('', {}));

    def test_no_headings(self):
        html = '<p>Test</p>'
        outh = '<div class="row"><div><div><p>Test</p></div></div></div>'
        self.assertEqual(outh, format_html(html, {}))

    def test_unknown_block_elements(self):
        """
        Ensure we don't remove block elements that we don't
        know about
        """
        html = '<foo>Test</foo>'
        outh = '<div class="row"><div><div><foo>Test</foo></div></div></div>'
        self.assertEqual(outh, format_html(html, {}))

    def test_existing_divs(self):
        html = "<div><foo><bar><fribble><div><div>Some text <p>para</p> some more</div><div> more <span> of </span> this stuff </div></div></fribble></bar></foo></div>"
        outh = '<div class="row"><div><div><foo><bar><fribble>Some text <p>para</p> some more more <span> of </span> this stuff </fribble></bar></foo></div></div></div>'
        self.assertEqual(outh, format_html(html, {}))

    def test_add_css_classes(self):
        html = "<h1>Hello <em>you</em></h1><h2>Hi</h2>"
        outh = '<div class="row"><div><div><h1 class=\"myclass\">Hello <em>you</em></h1><h2 class=\"c1 c2\">Hi</h2></div></div></div>'
        self.assertEqual(outh, format_html(html, {'h1_1':[PC('myclass')],
                                                  'h2_1':[PC('c1'), PC('c2')]}))

    def test_sanity_check_columns(self):
        """
        Check that user is not allowed to add column structure
        to blocks that aren't 'top level' in document structure
        """
        html = "<blockquote><p>How are you</p></blockquote>"
        pres = {'newrow_p_1': [NEWROW]}
        self.assertRaises(BadStructure, format_html, html, pres)

        html2 = "<blockquote><p>How are you</p></blockquote>"
        pres2 = {'newcol_p_1': [NEWROW]}
        self.assertRaises(BadStructure, format_html, html2, pres2)

    def test_columns_1(self):
        html = "<h1>1</h1><p>para 1</p><h1>2</h1><h1>3</h1>"
        outh = "<div class=\"row columns2\"><div class=\"column firstcolumn\"><div><h1>1</h1><p>para 1</p></div></div><div class=\"column lastcolumn\"><div><h1>2</h1><h1>3</h1></div></div></div>"
        self.assertEqual(outh, format_html(html, {'newrow_h1_1':[NEWROW],
                                                  'newcol_h1_2':[NEWCOL]}))

    def test_columns_with_double_width(self):
        html = "<h1>1</h1><p>para 1</p><h1>2</h1>"
        outh = "<div class=\"row columns3\"><div class=\"column firstcolumn doublewidth\"><div><h1>1</h1><p>para 1</p></div></div><div class=\"column lastcolumn\"><div><h1>2</h1></div></div></div>"
        self.assertEqual(outh, format_html(html, {'newrow_h1_1':[NEWROW],
                                                  'newcol_h1_1':[NEWCOL, PC('doublewidth', column_equiv=2)],
                                                  'newcol_h1_2':[NEWCOL]}))

    def test_columns_with_double_width_2(self):
        html = "<h1>1</h1><p>para 1</p><h1>2</h1>"
        outh = "<div class=\"row columns3\"><div class=\"column firstcolumn\"><div><h1>1</h1><p>para 1</p></div></div><div class=\"column lastcolumn doublewidth\"><div><h1>2</h1></div></div></div>"
        self.assertEqual(outh, format_html(html, {'newrow_h1_1':[NEWROW],
                                                  'newcol_h1_1':[NEWCOL],
                                                  'newcol_h1_2':[NEWCOL, PC('doublewidth', column_equiv=2)]}))

    def test_max_cols(self):
        """
        Check we can't exceed max cols
        """
        html = "<h1>1</h1><h1>2</h1><h1>3</h1><h1>4</h1><h1>5</h1>"
        self.assertRaises(TooManyColumns, format_html, html, {'newrow_h1_1':[NEWROW],
                                                              'newcol_h1_2':[NEWCOL],
                                                              'newcol_h1_3':[NEWCOL],
                                                              'newcol_h1_4':[NEWCOL],
                                                              'newcol_h1_5':[NEWCOL]
                                                            })
    def test_max_cols_2(self):
        """
        Check we can't exceed max cols with double width cols
        """
        html = "<h1>1</h1><h1>2</h1><h1>3</h1>"
        self.assertRaises(TooManyColumns, format_html, html, {'newrow_h1_1':[NEWROW],
                                                              'newcol_h1_1':[NEWCOL, PC('doublewidth', column_equiv=2)],
                                                              'newcol_h1_2':[NEWCOL, PC('doublewidth', column_equiv=2)],
                                                              'newcol_h1_3':[NEWCOL],

                                                            })


    def test_columns_2(self):
        html = \
            "<h1>1</h1>" \
            "<h1>2</h1>" \
            "<h2>2.1</h2>" \
            "<h2>2.2</h2>" \
            "<h2>2.3</h2>" \
            "<h2>2.4</h2>" \
            "<h1>3</h1>" \
            "<h1>4</h1>"

        outh = \
            "<div class=\"row\">" \
            "<div>" \
            "<div>" \
            "<h1>1</h1>" \
            "<h1>2</h1>" \
            "</div>" \
            "</div>" \
            "</div>" \
            "<div class=\"row columns2\">" \
            "<div class=\"column firstcolumn\">" \
            "<div>" \
            "<h2>2.1</h2>" \
            "</div>" \
            "</div>" \
            "<div class=\"column lastcolumn\">" \
            "<div>" \
            "<h2>2.2</h2>" \
            "</div>" \
            "</div>" \
            "</div>" \
            "<div class=\"row columns2\">" \
            "<div class=\"column firstcolumn\">" \
            "<div>" \
            "<h2>2.3</h2>" \
            "</div>" \
            "</div>" \
            "<div class=\"column lastcolumn\">" \
            "<div>" \
            "<h2>2.4</h2>" \
            "</div>" \
            "</div>" \
            "</div>" \
            "<div class=\"row columns2\">" \
            "<div class=\"column firstcolumn\">" \
            "<div>" \
            "<h1>3</h1>" \
            "</div>" \
            "</div>" \
            "<div class=\"column lastcolumn\">" \
            "<div>" \
            "<h1>4</h1>" \
            "</div>" \
            "</div>" \
            "</div>"
        self.assertEqual(outh, format_html(html, {'newrow_h2_1':[NEWROW],
                                                  'newcol_h2_2':[NEWCOL],
                                                  'newrow_h2_3':[NEWROW],
                                                  'newcol_h2_4':[NEWCOL],
                                                  'newrow_h1_3':[NEWROW],
                                                  'newcol_h1_4':[NEWCOL],
                                                  }))

    def test_layout_with_styling(self):
        html = "<h1>1</h1><p>para 1</p><h1>2</h1><h1>3</h1>"
        outh = "<div class=\"row columns2 fancyrow\"><div class=\"column firstcolumn\"><div><h1>1</h1><p>para 1</p></div></div><div class=\"column lastcolumn\"><div class=\"fancycol\"><h1>2</h1><h1>3</h1></div></div></div>"
        self.assertEqual(outh, format_html(html, {'newrow_h1_1':[NEWROW, PC('fancyrow')],
                                                  'newcol_h1_2':[NEWCOL, PC('fancycol')]}))

    def test_columns_single_col(self):
        html = "<h1>1</h1><p>para 1</p><h2>2</h2>"
        outh = "<div class=\"row\"><div><div><h1>1</h1><p>para 1</p><h2>2</h2></div></div></div>"
        self.assertEqual(outh, format_html(html, {'h1_1':[NEWROW]}))

class TestElementTreeUtils(TestCase):
    def test_get_parent(self):
        """
        Tests that get_parent works
        """
        t = parse("<a><b1></b1><b2></b2></a>")
        n = t.find(".//b2")
        p = get_parent(t, n)
        self.assertEqual(p, t.find(".//a"))

    def test_get_index(self):
        """
        Tests that get_index returns the index of node amongst its siblings
        """
        t = parse("<a><b1></b1><b2></b2></a>")
        n = t.find(".//b2")
        p = get_parent(t, n)
        self.assertEqual(1, get_index(p,n))


class TestExtractPresentation(TestCase):
    def test_extract_presentation(self):
        html = "<h1 class=\"foo\">Heading 1</h1><h2 class=\"bar baz\">Heading 2</h2><p class=\"whatsit\">Some paragraph</p>"
        pres, html2 = extract_presentation(html)
        self.assertEqual({'h1_1':set([PC('foo')]),
                          'h2_1':set([PC('bar'), PC('baz')]),
                          'p_1':set([PC('whatsit')]),
                          }, pres)
        self.assertEqual("<h1 id=\"h1_1\">Heading 1</h1><h2 id=\"h2_1\">Heading 2</h2><p id=\"p_1\">Some paragraph</p>", html2)

    # Lazy method - assume that combine works and check the round-trip.
    # This only works currently if we 'normalise' the presentation dict.
    def test_extract_1(self):
        html = \
            "<h1>1</h1>" \
            "<h1>2</h1>" \
            "<h2>2.1</h2>" \
            "<h2>2.2</h2>" \
            "<h2>2.3</h2>" \
            "<h2>2.4</h2>" \
            "<h1>3</h1>" \
            "<h1>4</h1>"

        presentation = {'h1_1':set([PC('myclass1')]),
                        'h1_2':set([]),
                        'h1_3':set([]),
                        'h1_4':set([]),
                        'h2_1':set([]),
                        'h2_2':set([]),
                        'h2_3':set([]),
                        'h2_4':set([]),
                        'newrow_h1_1':set([NEWROW]),
                        'newcol_h1_1':set([NEWCOL]),
                        'newrow_h2_1':set([NEWROW]),
                        'newcol_h2_1':set([NEWCOL]),
                        'newcol_h2_2':set([NEWCOL]),
                        'newrow_h2_3':set([NEWROW]),
                        'newcol_h2_3':set([NEWCOL]),
                        'newcol_h2_4':set([NEWCOL, PC('myclass2')]),
                        'newrow_h1_3':set([NEWROW]),
                        'newcol_h1_3':set([NEWCOL]),
                        'newcol_h1_4':set([NEWCOL]),
                        }
        combined = format_html(html, presentation)
        pres2, html2 = extract_presentation(combined)
        self.assertEqual(presentation, pres2)

    def test_extract_2(self):
        # Full featured, proper test
        html = """
<div class="row columns3"><div class="column firstcolumn"><div class="myclass"><h1>Hello Jane</h1><p>Some fancy content, entered using WYMeditor</p><p>Another paragraph</p><p>Hello</p></div></div><div class="column doublewidth"><div><h1>Another &lt;heading&gt;</h1><h2>this is a test</h2><h2>hello1</h2><h3>hello2</h3><h3>hello3</h3><h3>hello4</h3></div></div><div class="column lastcolumn"><div><h1>hello5</h1><h2>hello6</h2><p>asdasd</p><p>asdxx</p></div></div></div>
"""
        pres = {'newrow_h1_1':set([NEWROW]),
                'newcol_h1_1':set([NEWCOL, PC('myclass')]),
                'h1_1':set(),
                'newcol_h1_2':set([NEWCOL, PC('doublewidth', column_equiv=2)]),
                'h1_2':set(),
                'p_1': set(),
                'p_2': set(),
                'p_3': set(),
                'h2_1':set(),
                'h2_2':set(),
                'h3_1':set(),
                'h3_2':set(),
                'h3_3':set(),
                'newcol_h1_3':set([NEWCOL]),
                'h1_3':set(),
                'h2_3':set(),
                'p_4': set(),
                'p_5': set(),
                }

        pres2, html2 = extract_presentation(html)
        self.assertEqual(pres, pres2)

    def test_extract_3(self):
        # Tests some other boundary conditions e.g. 1 column row,
        html = """
<div class="row"><div><div><h1>1</h1><h2>1.1</h2><h2>1.2</h2></div></div></div>
"""
        pres = {'h1_1': set(),
                'newrow_h1_1':set([NEWROW]),
                'newcol_h1_1':set([NEWCOL]),
                'h2_1': set(),
                'h2_2': set(),
                }
        pres2, html2 = extract_presentation(html)
        self.assertEqual(pres, pres2)

    def test_extract_no_inner_col_div_1(self):
        # Tests that we can extract column structure if we don't have
        # an inner column div.
        # This is important for the case where LayoutDetails.use_inner_column_div = False

        # Single col structure
        html = """
<div class="row"><div><h1>1</h1><h2>1.1</h2><h2>1.2</h2></div></div>
"""
        pres = {'h1_1': set(),
                'newrow_h1_1':set([NEWROW]),
                'newcol_h1_1':set([NEWCOL]),
                'h2_1': set(),
                'h2_2': set(),
                }
        pres2, html2 = extract_presentation(html)
        self.assertEqual(pres, pres2)

    def test_extract_no_inner_col_div_2(self):
        # Tests that we can extract column structure if we don't have 
        # an inner column div.
        # This is important for the case where LayoutDetails.use_inner_column_div = False

        # Double col structure
        html = """
<div class="row"><div class="column firstcolumn"><h1>1</h1></div><div class="column lastcolumn"><h2>1.1</h2></div></div>
"""
        pres = {'h1_1': set(),
                'newrow_h1_1':set([NEWROW]),
                'newcol_h1_1':set([NEWCOL]),
                'h2_1': set(),
                'newcol_h2_1':set([NEWCOL])
                }
        pres2, html2 = extract_presentation(html)
        self.assertEqual(pres, pres2)
