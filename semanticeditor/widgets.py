from cms.admin.editors.wymeditor.widgets import WYMEditor
from cms.admin.editors.wymeditor import settings
from cms.settings import CMS_MEDIA_URL
from django import forms
from django.conf import settings as global_settings
from django.utils.safestring import mark_safe
from django.utils.translation.trans_real import get_language
from django.template.loader import render_to_string
import os

join = os.path.join

class SemanticEditor(WYMEditor):
    class Media:
        js = [join(global_settings.SE_MEDIA_URL, path) for path in
              ('javascript/wymeditor/plugins/semantic/wymeditor.semantic.js',
               'javascript/json2.js',
               'javascript/orbitaltooltip.js',
               )]

    def render_additions(self, name, value, attrs=None):
        language = get_language()
        context = {
            'name': name,
            'language': language,
            'SE_MEDIA_URL': global_settings.SE_MEDIA_URL,
            'CMS_MEDIA_URL': CMS_MEDIA_URL,
            'WYM_TOOLS': mark_safe(settings.WYM_TOOLS),
            'WYM_CONTAINERS': mark_safe(settings.WYM_CONTAINERS),
            'WYM_CLASSES': mark_safe(settings.WYM_CLASSES),
        }

        return mark_safe(render_to_string(
            'semanticeditor/editorwidget.html', context))
