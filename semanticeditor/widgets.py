# Override for widgets in django-cms

# Include all the normal ones
from cms.admin.widgets import *
from django import forms
from django.conf import settings
import os

join = os.path.join

class SemanticEditor(WYMEditor):
    class Media:
        js = [join(settings.SE_MEDIA_URL, path) for path in
              ('javascript/wymeditor/plugins/semantic/wymeditor.semantic.js',
               )]

    def render_extra(self, name, value, attrs=None):
        context = {
            'name': name,
            'language': self.language,
            'SE_MEDIA_URL': settings.SE_MEDIA_URL,
        }
        return mark_safe(render_to_string(
            'semanticeditor/editorwidget.html', context))
