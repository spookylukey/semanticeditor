from django.contrib import admin
from semanticeditor.models import CssClass, CssClassCategory

class CssClassAdmin(admin.ModelAdmin):
    pass

admin.site.register(CssClass, CssClassAdmin)
admin.site.register(CssClassCategory)
