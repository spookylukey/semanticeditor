# Override for widgets in django-cms

# Include all the normal ones
from cms.admin.widgets import *
from django import forms
from django.conf import settings


class SemanticEditor(WYMEditor):
    def _media(self):
        extra_media = forms.Media({})
        return super(SemanticEditor, self)._media() + extra_media

    def render_extra(self, name, value, attrs=None):
        context = {
            'name': name,
            'language': self.language,
            'SE_MEDIA_URL': settings.SE_MEDIA_URL,
        }
        return mark_safe(render_to_string(
            'semanticeditor/editorwidget.html', context))
