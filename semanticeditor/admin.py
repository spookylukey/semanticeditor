from django.contrib import admin
from semanticeditor.models import CssClass, CssClassCategory

class CssClassAdminInline(admin.StackedInline):
    model = CssClass
    extra = 0
    fieldsets = (
        (None, {
            'fields': (
                ('name', 'verbose_name'),
                ('description', 'templates',),
                ('allowed_elements', 'column_equiv'),
            ),
        }),
    )

class CssClassAdmin(admin.ModelAdmin):
    list_display = ('verbose_name', 'name', 'category', 'allowed_elements')
    list_editable = ('name', 'category', 'allowed_elements')

class CssClassCategoryAdmin(admin.ModelAdmin):
    inlines = [CssClassAdminInline,]
    
admin.site.register(CssClass, CssClassAdmin)
admin.site.register(CssClassCategory, CssClassCategoryAdmin)