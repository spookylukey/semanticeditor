from django.contrib import admin
from semanticeditor.models import CssClass

class CssClassAdmin(admin.ModelAdmin):
    pass

admin.site.register(CssClass, CssClassAdmin)

