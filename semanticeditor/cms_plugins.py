from cms.plugins.text.cms_plugins import TextPlugin
from cms.plugins.text.models import Text
from cms.plugins.text.forms import TextForm
from cms.plugin_pool import plugin_pool
from cms.plugin_base import CMSPluginBase
from django.utils.translation import ugettext_lazy as _

from semanticeditor.widgets import SemanticEditor
from cms.plugins.text.utils import plugin_tags_to_user_html
from django.forms.fields import CharField

class SemanticTextPlugin(TextPlugin):

    name = _("Text/layout")
    admin_preview = False

    def get_editor_widget(self, request, plugins):
        return SemanticEditor(installed_plugins=plugins)

plugin_pool.register_plugin(SemanticTextPlugin)
