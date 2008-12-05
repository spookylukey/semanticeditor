# -*- coding: utf-8 -*-

from django.test import TestCase
from semanticeditor.utils import extract_headings, InvalidHtml, IncorrectHeadings, format_html, parse, get_parent, get_index, BadStructure, TooManyColumns, NEWROW, NEWCOL, extract_presentation

class TestExtract(TestCase):
    def test_extract_headings(self):
        self.assertEqual(extract_headings("""
<h1>Heading <b>with </b><i>embedded <em>stuff</em> in</i> it</h1> Hmm<p>A paragraph</p>
<h2>A sub heading</h2><p>Another para</p>
<h3>level 3</h3>
<h4>level 4</h4>
<h5>level 5</h5>
<h6>level 6</h6>
<h1>Heading two</h1>
"""), [(1, "Heading with embedded stuff in it"),
       (2, "A sub heading"),
       (3, "level 3"),
       (4, "level 4"),
       (5, "level 5"),
       (6, "level 6"),
       (1, "Heading two"),
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

class TestFormat(TestCase):
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
        self.assertEqual(outh, format_html(html, {'Hello you':['class:myclass'],
                                                  'Hi':['class:c1', 'class:c2']}))

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
    def test_extract_style(self):
        html = "<div class=\"foo\"><h1>Heading 1</h1><div class=\"bar baz\"><h2>Heading 2</h2></div></div>"
        pres = extract_presentation(html)
        self.assertEqual({'Heading 1':set(['class:foo']),
                          'Heading 2':set(['class:bar', 'class:baz'])
                          }, pres)

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

        presentation = {'1':set(['class:myclass1']),
                        '2':set([]),
                        '2.1':set([NEWROW]),
                        '2.2':set([NEWCOL]),
                        '2.3':set([NEWROW]),
                        '2.4':set([NEWCOL, 'class:myclass2']),
                        '3':set([NEWROW]),
                        '4':set([NEWCOL]),
                        }
        combined = format_html(html, presentation)
        pres2 = extract_presentation(combined)
        self.assertEqual(presentation, pres2)
