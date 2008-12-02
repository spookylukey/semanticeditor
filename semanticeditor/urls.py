from django.conf.urls.defaults import patterns, url
from semanticeditor.views import extract_headings_view

urlpatterns = patterns('',
    url(r'extract_headings/', extract_headings_view),
)
