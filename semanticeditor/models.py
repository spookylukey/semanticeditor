from django.db import models
from semanticeditor.fields import MultiSelectField
from django.conf import settings


template_list = [(f,n) for (f,n) in settings.CMS_TEMPLATES if f != settings.CMS_TEMPLATE_INHERITANCE_MAGIC]


class CssClassCategory(models.Model):
    name = models.CharField("Category name", max_length=255, unique=True)

    def __unicode__(self):
        return self.name


    class Meta:
        verbose_name = "CSS class category"
        verbose_name_plural = "CSS class categories"
        ordering = ('name',)


class CssClass(models.Model):
    category = models.ForeignKey(CssClassCategory, null=True, blank=True)
    name = models.CharField("CSS class name", max_length=255, unique=True,
                                  help_text="The name as it appears in the CSS file")
    verbose_name = models.CharField("Human name", max_length=255, blank=False, unique=True,
                                    help_text="User-visible name of the style.")
    description = models.TextField("Description", max_length=255, blank=True,
                                   help_text="This is displayed as a 'tooltip' "
                                   "when the user hovers over the name in the "
                                   "list of styles.  The data will be interpreted "
                                   "as raw HTML, so it can include an example.")
    templates = MultiSelectField("Templates", choices=template_list, blank=True,
                                 default="")

    allowed_elements = models.CharField("Allowed HTML elements", max_length=255,
                                        help_text="A space separated list of HTML "
                                        "element names.  Use 'newrow'/'newcol'/"
                                        "'innerrow'/'innercol' to indicate "
                                        "it can be applied to layout rows or columns ",
                                        default="h1 h2 h3 h4 h5 h6 p blockquote ul ol li newrow newcol")

    column_equiv = models.IntegerField("Column count equivalent", null=True, blank=True,
                                       help_text="For classes designed to be applied to "
                                       "columns only, this is the number of columns this "
                                       "should be considered as equivalent to. This can be "
                                       "useful for generating double width columns etc. "
                                       "within a column layout.")
    def __unicode__(self):
        return self.verbose_name

    class Meta:
        verbose_name = "CSS class"
        verbose_name_plural = "CSS classes"
        ordering = ('verbose_name',)


def get_classes(template):
    # Can't do filter in DB easily, because 'templates' is actually a comma
    # separated list in DB.
    classes = CssClass.objects.all().order_by('category__name', 'verbose_name')
    return filter(lambda c: template in c.templates, classes)
