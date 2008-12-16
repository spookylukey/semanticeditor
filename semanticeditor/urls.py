from django.conf.urls.defaults import patterns, url
from semanticeditor.views import extract_headings_view, retrieve_styles, separate_presentation, combine_presentation, preview

urlpatterns = patterns('',
    url(r'extract_headings/', extract_headings_view, name="semantic.extract_headings"),
    url(r'retrieve_styles/', retrieve_styles, name="semantic.retrieve_styles"),
    url(r'separate_presentation/', separate_presentation, name="semantic.separate_presentation"),
    url(r'combine_presentation/', combine_presentation, name="semantic.combine_presentation"),
    url(r'preview/', preview, name="semantic.preview"),
)
