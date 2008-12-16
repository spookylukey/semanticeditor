from cms.plugins.text.widgets import WYMEditor
from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation.trans_real import get_language
from django.template.loader import render_to_string
import os

join = os.path.join

class SemanticEditor(WYMEditor):
    class Media:
        js = [join(settings.SE_MEDIA_URL, path) for path in
              ('javascript/wymeditor/plugins/semantic/wymeditor.semantic.js',
               'javascript/json2.js',
               'javascript/orbitaltooltip.js',
               )]

    def render_additions(self, name, value, attrs=None):
        language = get_language()
        context = {
            'name': name,
            'language': language,
            'SE_MEDIA_URL': settings.SE_MEDIA_URL,
        }

        return mark_safe(render_to_string(
            'semanticeditor/editorwidget.html', context))
