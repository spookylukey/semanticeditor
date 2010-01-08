# -*- coding: utf-8 -*-

from django.test import TestCase
from semanticeditor.utils import *


PC = PresentationClass

class TestExtractStructure(TestCase):
    def test_extract_structure(self):
        self.assertEqual([(s.level, s.sect_id, s.name, s.tag) for s in extract_structure(u"""
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
        [(1, "h1_1", u"Heading with embedded stuff in it", u"h1"),
         (2, "p_1", u"A long paragraph with some actual content...", u"p"),
         (2, "h2_1", u"A sub heading", u"h2"),
         (3, "p_2", u"Another para...", u"p"),
         (3, "h3_1", u"level 3", u"h3"),
         (4, "p_3", u"A long paragraph with some actual content...2", u"p"),
         (4, "h4_1", u"level 4", u"h4"),
         (5, "p_4", u"Another para...2", u"p"),
         (5, "h5_1", u"level 5", u"h5"),
         (6, "p_5", u"nasty  éééééééééééééééééééééééééé...", u"p"),
         (6, "h6_1", u"level 6", u"h6"),
         (1, "h1_2", u"Heading two", u"h1"),
         ])

    def test_extract_structure_missing(self):
        self.assertEqual(extract_structure(""), [])

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
    def setUp(self):
        # monkey patch to ensure some assumptions we make about LayoutDetails.
        # We may have to go the whole hog and do dependency injection at some
        # point.
        self._old_max_columns = LayoutDetails.max_columns
        LayoutDetails.max_columns = 4
        super(TestCase, self).setUp()

    def tearDown(self):
        LayoutDetails.max_columns = self._old_max_columns
        super(TestCase, self).tearDown()

    def test_remove_command_divs(self):
        self.assertEqual('<div class="row"><div><div><p>Test</p></div></div></div>', format_html('<div class="newrow">* </div><p>Test</p>', {}))
        self.assertEqual('<div class="row"><div><div><p>Test</p></div></div></div>', format_html('<p class="newrow">* </p><p>Test</p>', {}))

    def test_empty(self):
        self.assertEqual('<div class="row"/>', format_html('', {}));

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
        outh = '<div class="row"><div><div><p><foo><bar><fribble><p>Some text para some more more  of  this stuff </p></fribble></bar></foo></p></div></div></div>'
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

    def test_format_pre(self):
        html = "<pre>This\r\nis\r\na\r\ntest</pre>"
        # check that format_html doesn't do anything nasty inside the pre
        html2 = format_html(html, {})
        pres, html3 = extract_presentation(html2)
        self.assertEqual(html, html3)


class TestHacks(TestCase):
    def test_div_format_hack(self):
        """
        Check that we can convert 'p' tags into 'div' using the 'div' class hack
        """
        html = '<p>Test</p>'
        outh = '<div class=\"row\"><div><div><div class="div">Test</div></div></div></div>'
        self.assertEqual(outh, format_html(html, {'p_1':[PC('div')]}))

    def test_div_extract_hack(self):
        """
        Check that a div with class "div" is recognised and turned back into a 'p'
        when extracting
        """
        html = '<div class="div">Test</div>'
        pres, html2 = extract_presentation(html)
        self.assertEqual({'p_1':set([PC('div')])}, pres)
        self.assertEqual('<p id="p_1">Test</p>', html2);

    def test_plugin_p_hack(self):
        """
        Check that a 'p' with only a plugin object is converted to a 'div'
        """
        # NB: current implementation of plugin objects is that they are
        # represented by an image in the editor.  Our code has to run before
        # these are converted, so we have to work with this implementation detail.
        html = '<p> <img src="blah" id="plugin_obj_123"/></p>'
        outh = '<div class="row"><div><div><div class="div"> <img src="blah" id="plugin_obj_123"/></div></div></div></div>'
        self.assertEqual(outh, format_html(html, {}))

    def test_plugin_p_hack_empty_only(self):
        """
        Check that if 'p' has any text in it, it is not converted
        """
        html = '<p>X <img src="blah" id="plugin_obj_123" /></p>'
        outh = '<div class="row"><div><div><p>X <img src="blah" id="plugin_obj_123"/></p></div></div></div>'
        self.assertEqual(outh, format_html(html, {}))
        html2 = '<p> <img src="blah" id="plugin_obj_123" />X</p>'
        outh2 = '<div class="row"><div><div><p> <img src="blah" id="plugin_obj_123"/>X</p></div></div></div>'
        self.assertEqual(outh2, format_html(html2, {}))


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
        self.assertEqual(1, get_index(p, n))

    def test_eliminate_tag_1(self):
        t = ET.fromstring("<a>Hello<b>Goodbye</b>End</a>")
        eliminate_tag(t, 0)
        self.assertEqual("<a>HelloGoodbyeEnd</a>", ET.tostring(t))

    def test_eliminate_tag_2(self):
        t = ET.fromstring("<a>Hello<b>Goodbye</b>Some<b>More</b>End</a>")
        eliminate_tag(t, 0)
        self.assertEqual("<a>HelloGoodbyeSome<b>More</b>End</a>", ET.tostring(t))

    def test_eliminate_tag_3(self):
        t = ET.fromstring("<a>Hello<b>Goodbye</b>Some<b>More</b>End</a>")
        eliminate_tag(t, 1)
        self.assertEqual("<a>Hello<b>Goodbye</b>SomeMoreEnd</a>", ET.tostring(t))

    def test_eliminate_tag_4(self):
        t = ET.fromstring("<a>Hello<b>Good<x>b</x><y>y</y>e</b>End</a>")
        eliminate_tag(t, 0)
        self.assertEqual("<a>HelloGood<x>b</x><y>y</y>eEnd</a>", ET.tostring(t))

    def test_eliminate_tag_5(self):
        t = ET.fromstring("<a>Hello<b>First <c>node</c></b>tail<b>Good<x>b</x><y>y</y>e</b>And<b>Stuff</b></a>")
        eliminate_tag(t, 1)
        self.assertEqual("<a>Hello<b>First <c>node</c></b>tailGood<x>b</x><y>y</y>eAnd<b>Stuff</b></a>", ET.tostring(t))



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


class TestHtmlCleanup(TestCase):
    safari_example_1 = """
<p style="margin-top: 0px; margin-right: 0px; margin-bottom: 0.8em; margin-left: 0px; padding-top: 0px; padding-right: 0px; padding-bottom: 0px; padding-left: 0px; font-size: 0.9em; line-height: 1.4em; "><strong style="font-weight: bold; ">Formerly: Community Health Sciences Research (CHSR) IRG</strong></p><p style="margin-top: 0px; margin-right: 0px; margin-bottom: 0.8em; margin-left: 0px; padding-top: 0px; padding-right: 0px; padding-bottom: 0px; padding-left: 0px; font-size: 0.9em; line-height: 1.4em; ">The Clinical Epidemiology IRG aims to undertake research that makes an important difference to patient care. Our work is divided into two broad research areas:</p><h4 style="color: rgb(153, 0, 51); margin-top: 0px; margin-right: 0px; margin-bottom: 0.25em; margin-left: 0px; padding-top: 0px; padding-right: 0px; padding-bottom: 0px; padding-left: 0px; font-size: 1.1em; line-height: 1.3em; "><strong style="font-weight: bold; ">Clinical and environmental epidemiology -</strong>&#160;including</h4><ul style="margin-top: 0px; margin-right: 0px; margin-bottom: 1.5em; margin-left: 0px; padding-top: 0px; padding-right: 0px; padding-bottom: 0px; padding-left: 0px; line-height: 1.4em; font-size: 0.9em; "><li style="margin-top: 0px; margin-right: 0px;margin-bottom: 0.25em; margin-left: 20px; padding-top: 0px; padding-right: 0px; padding-bottom: 0px;padding-left: 0px; ">mental health</li><li style="margin-top: 0px; margin-right: 0px; margin-bottom: 0.25em; margin-left: 20px; padding-top: 0px; padding-right: 0px; padding-bottom: 0px; padding-left: 0px; ">child protection</li><li style="margin-top: 0px; margin-right: 0px; margin-bottom: 0.25em; margin-left: 20px; padding-top: 0px; padding-right: 0px; padding-bottom: 0px; padding-left: 0px;">cancer</li><li style="margin-top: 0px; margin-right: 0px; margin-bottom: 0.25em; margin-left: 20px; padding-top: 0px; padding-right: 0px; padding-bottom: 0px; padding-left: 0px; ">environmental, economic and social risk factors</li></ul></span>
"""
    safari_output_1 = """
<p><strong>Formerly: Community Health Sciences Research (CHSR) IRG</strong></p><p>The Clinical Epidemiology IRG aims to undertake research that makes an important difference to patient care. Our work is divided into two broad research areas:</p><h4><strong>Clinical and environmental epidemiology -</strong>&#160;including</h4><ul><li>mental health</li><li>child protection</li><li>cancer</li><li>environmental, economic and social risk factors</li></ul>"""

    firefox_oowriter_example_1 = u"""
<style type="text/css">
	&lt;!--
		@page { margin: 2cm }
		P { margin-bottom: 0.21cm }
		H2 { margin-bottom: 0.21cm }
		H2.western { font-family: "Bitstream Vera Sans", sans-serif; font-size: 14pt; font-style: italic }
		H2.cjk { font-family: "DejaVu Sans"; font-size: 14pt; font-style: italic }
		H2.ctl { font-family: "DejaVu Sans"; font-size: 14pt; font-style: italic }
	--&gt;
	</style><p class="western"><strong>My Café</strong></p><h2 class="western">Heading</h2><table width="459" cellpadding="4"><col width="110"><col width="334"><tbody><tr><td><p class="western">cell1</p></td><td><p class="western">cell2</p></td></tr></tbody><p class="western"></p><h2 class="western">Heading 2</h2><p class="western"></p><p class="western">Some “text”</p></col>
"""
    firefox_oowriter_output_1 = u"""
<p><strong>My Caf&#233;</strong></p><h2>Heading</h2><p>cell1</p><p>cell2</p><h2>Heading 2</h2><p>Some “text”</p>
"""

    def assertEqualClean(self, input, output):
        """
        Assert that expected output is the same as the input cleaned
        """
        # Do a pretty_print to make error messages nicer
        actual_output = clean_html(input)
        s1 = pretty_print(output).strip()
        s2 = pretty_print(actual_output).strip()
        try:
            self.assertEqual(s1, s2)
        except:
            print
            print s1
            print
            print s2
            raise

    def test_cleanup_safari_1(self):
        self.assertEqualClean(self.safari_example_1,
                              self.safari_output_1)

    def test_cleanup_firefox_oowriter_1(self):
        self.assertEqualClean(self.firefox_oowriter_example_1,
                              self.firefox_oowriter_output_1)

    def test_cleanup_tables(self):
        self.assertEqualClean("<table><tbody><tr><td><p>Hello</p></td></tr></tbody><p>P2</p>text</table>",
                              "<p>Hello</p><p>P2</p><p>text</p>");

    def test_toplevel_text(self):
        # Make sure that text at the top level is inside some tag
        self.assertEqualClean("test", "<p>test</p>")

    def test_div_to_p(self):
        self.assertEqualClean("<div>Foo</div>", "<p>Foo</p>")

    def test_nested_p(self):
        self.assertEqualClean("<p>Hello <p>How are <p>you</p></p> today</p>",
                              "<p>Hello </p><p>How are </p><p>you</p><p> today</p>")

    def test_br_to_p(self):
        self.assertEqualClean("This is<br /><br />a test",
                              "<p>This is</p><p>a test</p>")

    def test_br_in_p(self):
        self.assertEqualClean("<p>line 1<br />line 2<br />line 3</p>",
                              "<p>line 1<br />line 2<br />line 3</p>")

    def test_p_in_li(self):
        self.assertEqualClean("<ul><li><p>An item</p></li></ul>",
                              "<ul><li>An item</li></ul>")

    def test_remove_span(self):
        self.assertEqualClean("<p>Some <span>text</span> with a silly span</p>",
                              "<p>Some text with a silly span</p>")

    def test_inline_wrapping_block(self):
        self.assertEqualClean("<strong><p>A test</p></strong>",
                              "<p>A test</p>")
        self.assertEqualClean("<em><ul><li>A test</li></ul></strong>",
                              "<ul><li>A test</li></ul>")

    def test_duplicate_ids(self):
        self.assertEqualClean('<p id="p_1">test</p><p id="p_1">test 2</p>' +
                              '<ul id="ul_1">test</ul><ul id="ul_1">test 2</p>',
                              '<p id="p_1">test</p><p>test 2</p>' +
                              '<ul id="ul_1">test</ul><ul>test 2</ul>')

