from django.conf.urls.defaults import patterns, url
from semanticeditor.views import extract_headings_view, retrieve_styles

urlpatterns = patterns('',
    url(r'extract_headings/', extract_headings_view),
    url(r'retrieve_styles/', retrieve_styles)
)
