from cms.plugins.text import settings as wym_settings
from cms.plugins.text.widgets.wymeditor_widget import WYMEditor
from cms.settings import CMS_MEDIA_URL
from django import forms
from django.conf import settings as global_settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation.trans_real import get_language
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
            'WYM_TOOLS': mark_safe(wym_settings.WYM_TOOLS),
            'WYM_CONTAINERS': mark_safe(wym_settings.WYM_CONTAINERS),
            'WYM_CLASSES': mark_safe(wym_settings.WYM_CLASSES),
            'installed_plugins': self.installed_plugins,
        }

        return mark_safe(render_to_string(
            'semanticeditor/editorwidget.html', context))
