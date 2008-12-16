# -*- coding: utf-8 -*-

from django.test import TestCase
from semanticeditor.utils import extract_headings, InvalidHtml, IncorrectHeadings, format_html, parse, get_parent, get_index, BadStructure, TooManyColumns, NEWROW, NEWCOL, extract_presentation
from semanticeditor.utils.presentation import PresentationInfo, PresentationClass

PC = PresentationClass

class TestExtractStructure(TestCase):
    def test_extract_headings(self):
        self.assertEqual(extract_headings("""
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
"""), [(1, u"Heading with embedded stuff in it", u"H1"),
       (2, u"A long paragraph wit...", u"P"),
       (2, u"A sub heading", u"H2"),
       (3, u"Another para...", u"P"),
       (3, u"level 3", u"H3"),
       (4, u"A long paragraph wit...2", u"P"),
       (4, u"level 4", u"H4"),
       (5, u"Another para...2", u"P"),
       (5, u"level 5", u"H5"),
       (6, u"nasty  ééééééééééééé...", u"P"),
       (6, u"level 6", u"H6"),
       (1, u"Heading two", u"H1"),
       ])

    def test_extract_headings_missing(self):
        self.assertEqual(extract_headings("Hello"), [])

    def test_rejects_bad_html(self):
        self.assertRaises(InvalidHtml, extract_headings, "<h1>Foo")

    def test_rejects_headings_not_start_at_1(self):
        self.assertRaises(IncorrectHeadings, extract_headings, "<h2>Hello</h2>")

    def test_rejects_improper_headings(self):
        self.assertRaises(IncorrectHeadings, extract_headings, "<h1>Hello</h1><h3>Bad heading</h3>")

    def test_rejects_duplicate_headings(self):
        self.assertRaises(IncorrectHeadings, extract_headings, "<h1>Hello</h1><h2>Hello</h2>")

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
        self.assertEqual('', format_html('', {}));

    def test_no_headings(self):
        html = "<p>Test</p>"
        self.assertEqual(html, format_html(html, {}))

    def test_creates_section_divs(self):
        html = "<h1>Hello</h1><p>P 1</p><h2>Heading 2</h2> trailing text<h1>Another</h1><p>So</p> trail"
        outh = "<div><h1>Hello</h1><p>P 1</p><div><h2>Heading 2</h2> trailing text</div></div><div><h1>Another</h1><p>So</p> trail</div>"
        self.assertEqual(outh, format_html(html, {}))

    def test_existing_divs(self):
        html = "<div><foo><bar><fribble><div><div>Some text <p>para</p> some more</div><div> more <span> of </span> this stuff </div></div></fribble></bar></foo></div>"
        outh = "<foo><bar><fribble>Some text <p>para</p> some more more <span> of </span> this stuff </fribble></bar></foo>"
        self.assertEqual(outh, format_html(html, {}))

    def test_add_css_classes(self):
        html = "<h1>Hello <em>you</em></h1><h2>Hi</h2>"
        outh = "<div class=\"myclass\"><h1>Hello <em>you</em></h1><div class=\"c1 c2\"><h2>Hi</h2></div></div>"
        self.assertEqual(outh, format_html(html, {'Hello you':[PC('myclass')],
                                                  'Hi':[PC('c1'), PC('c2')]}))

    def test_sanity_check_sections(self):
        html = "<h1>Hello</h1><blockquote><h2>Hi</h2></blockquote>"
        self.assertRaises(BadStructure, format_html, html, {})

    def test_columns_1(self):
        html = "<h1>1</h1><p>para 1</p><h1>2</h1><h1>3</h1>"
        outh = "<div class=\"row2col\"><div class=\"col\"><div><h1>1</h1><p>para 1</p></div></div><div class=\"col\"><div><h1>2</h1></div><div><h1>3</h1></div></div></div>"
        self.assertEqual(outh, format_html(html, {'1':[NEWROW],
                                                  '2':[NEWCOL]}))

    def test_max_cols(self):
        html = "<h1>1</h1><h1>2</h1><h1>3</h1><h1>4</h1><h1>5</h1>"
        self.assertRaises(TooManyColumns, format_html, html, {'1':[NEWROW],
                                                              '2':[NEWCOL],
                                                              '3':[NEWCOL],
                                                              '4':[NEWCOL],
                                                              '5':[NEWCOL]
                                                            })

    def test_creates_section_divs_2(self):
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
            "<div><h1>1</h1></div>" \
            "<div><h1>2</h1>" \
            "<div><h2>2.1</h2></div>" \
            "<div><h2>2.2</h2></div>" \
            "<div><h2>2.3</h2></div>" \
            "<div><h2>2.4</h2></div>" \
            "</div>" \
            "<div><h1>3</h1></div>" \
            "<div><h1>4</h1></div>"
        self.assertEqual(outh, format_html(html, {}))


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
            "<div><h1>1</h1></div>" \
            "<div><h1>2</h1>" \
            "<div class=\"row2col\">" \
            "<div class=\"col\">" \
            "<div><h2>2.1</h2></div>" \
            "</div>" \
            "<div class=\"col\">" \
            "<div><h2>2.2</h2></div>" \
            "</div>" \
            "</div>" \
            "<div class=\"row2col\">" \
            "<div class=\"col\">" \
            "<div><h2>2.3</h2></div>" \
            "</div>" \
            "<div class=\"col\">" \
            "<div><h2>2.4</h2></div>" \
            "</div>" \
            "</div>" \
            "</div>" \
            "<div class=\"row2col\">" \
            "<div class=\"col\">" \
            "<div><h1>3</h1></div>" \
            "</div>" \
            "<div class=\"col\">" \
            "<div><h1>4</h1></div>" \
            "</div>" \
            "</div>"
        self.assertEqual(outh, format_html(html, {'2.1':[NEWROW],
                                                  '2.2':[NEWCOL],
                                                  '2.3':[NEWROW],
                                                  '2.4':[NEWCOL],
                                                  '3':[NEWROW],
                                                  '4':[NEWCOL],
                                                  }))

    def test_columns_missing_newrow(self):
        html = "<h1>1</h1><p>para 1</p><h1>2</h1><h1>3</h1>"
        self.assertRaises(BadStructure, format_html, html, {'2':[NEWCOL]})

    def test_columns_nested_newcols(self):
        """
        Check that attempting to add columns at a different level
        will generate an error
        """
        html = "<h1>1</h1><h2>1.1</h2><h1>2</h1>"
        self.assertRaises(BadStructure, format_html, html, {'1':[NEWROW],
                                                            '1.1':[NEWCOL]})
    def test_columns_nested_newrow(self):
        """
        Check that attempting to add new row at a different level
        will generate an error
        """
        html = "<h1>1</h1><h2>1.1</h2>"
        self.assertRaises(BadStructure, format_html, html, {'1':[NEWROW],
                                                            '1.1':[NEWROW]})


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
        html = "<div class=\"foo\"><h1>Heading 1</h1><div class=\"bar baz\"><h2>Heading 2</h2></div></div>"
        pres, html2 = extract_presentation(html)
        self.assertEqual({'Heading 1':set([PC('foo')]),
                          'Heading 2':set([PC('bar'), PC('baz')])
                          }, pres)
        self.assertEqual("<h1>Heading 1</h1><h2>Heading 2</h2>", html2)

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

        presentation = {'1':set([PC('myclass1')]),
                        '2':set([]),
                        '2.1':set([NEWROW]),
                        '2.2':set([NEWCOL]),
                        '2.3':set([NEWROW]),
                        '2.4':set([NEWCOL, PC('myclass2')]),
                        '3':set([NEWROW]),
                        '4':set([NEWCOL]),
                        }
        combined = format_html(html, presentation)
        pres2, html2 = extract_presentation(combined)
        self.assertEqual(presentation, pres2)
        self.assertEqual(html, html2)

    def test_extract_2(self):
        html = """
<div class="row3col"><div class="col"><div><h1>Hello Jane</h1><p>Some fancy content, entered using WYMeditor</p><p>Another paragraph</p><p>Hello</p></div></div><div class="col"><div><h1>Another &lt;heading&gt;</h1><div><h2>this is a test</h2></div><div><h2>hello1</h2><div><h3>hello2</h3></div><div><h3>hello3</h3></div><div><h3>hello4</h3></div></div></div></div><div class="col"><div><h1>hello5</h1><div><h2>hello6</h2><p>asdasd</p><p>asdxx</p></div></div></div></div>
"""
        pres = {'Hello Jane':set([NEWROW]),
                'Another <heading>':set([NEWCOL]),
                'this is a test':set(),
                'hello1':set(),
                'hello2':set(),
                'hello3':set(),
                'hello4':set(),
                'hello5':set([NEWCOL]),
                'hello6':set()
                }

        pres2, html2 = extract_presentation(html)
        self.assertEqual(pres, pres2)

    def test_extract_3(self):
        # Tests some other boundary conditions e.g. 1 column row,
        # multiple sections within the column.
        html = """
<div><h1>1</h1><div class="row1col"><div class="col"><div><h2>1.1</h2></div><div><h2>1.2</h2></div></div></div></div>
"""
        pres = {'1': set(),
                '1.1':set([NEWROW]),
                '1.2': set(),
                }
        pres2, html2 = extract_presentation(html)
        self.assertEqual(pres, pres2)
