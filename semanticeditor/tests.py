# -*- coding: utf-8 -*-

from django.test import TestCase
from semanticeditor.utils import extract_headings, InvalidHtml, IncorrectHeadings, format_html, parse, get_parent, get_index

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
        html = "<h1>Hello</h1><p>P 1</p><h2>Heading 2</h2><h1>Another</h1><p>So</p>"
        outh = "<div><h1>Hello</h1><p>P 1</p><div><h2>Heading 2</h2></div></div><div><h1>Another</h1><p>So</p></div>"
        self.assertEqual(outh, format_html(html, {}))

    def test_existing_divs(self):
        html = "<div><foo><bar><fribble><div><div>Some text <p>para</p> some more</div><div> more <span> of </span> this stuff </div></div></fribble></bar></foo></div>"
        outh = "<foo><bar><fribble>Some text <p>para</p> some more more <span> of </span> this stuff </fribble></bar></foo>"
        self.assertEqual(outh, format_html(html, {}))

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

