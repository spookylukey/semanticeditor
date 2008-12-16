from cms.plugin_pool import plugin_pool
from cms.plugin_base import CMSPluginBase
from django.utils.translation import ugettext_lazy as _
from cms.plugins.text.models import Text
from semanticeditor.forms import SemanticTextForm

class SemanticTextPlugin(CMSPluginBase):
    model = Text
    name = _("Text with presentation")
    form = SemanticTextForm

    def render(self, request, instance):
        return instance.body

plugin_pool.register_plugin(SemanticTextPlugin)
