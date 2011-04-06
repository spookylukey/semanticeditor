from django.contrib import admin
from semanticeditor.models import CssClass, CssClassCategory


class CssClassAdmin(admin.ModelAdmin):
    list_display = ('verbose_name', 'name', 'category')


admin.site.register(CssClass, CssClassAdmin)
admin.site.register(CssClassCategory)
