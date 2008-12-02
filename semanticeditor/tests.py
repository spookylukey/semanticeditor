# -*- coding: utf-8 -*-

from django.test import TestCase
from semanticeditor.utils import extract_headings, InvalidHtml, IncorrectHeadings

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
