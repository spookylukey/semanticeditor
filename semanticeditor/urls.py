from django.conf.urls.defaults import patterns, url
from semanticeditor.views import extract_headings_view, retrieve_styles, separate_presentation, combine_presentation

urlpatterns = patterns('',
    url(r'extract_headings/', extract_headings_view),
    url(r'retrieve_styles/', retrieve_styles),
    url(r'separate_presentation/', separate_presentation),
    url(r'combine_presentation/', combine_presentation),
)
