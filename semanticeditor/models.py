from django.db import models

class CssClass(models.Model):
    name = models.CharField("CSS class name", max_length=255, unique=True,
                                  help_text="The name as it appears in the CSS file")
    verbose_name = models.CharField("Human name", max_length=255, blank=False, unique=True,
                                    help_text="User-visible name of the style.")
    description = models.TextField("Description", max_length=255, blank=True,
                                   help_text="This is displayed as a 'tooltip' "
                                   "when the user hovers over the name in the "
                                   "list of styles.  The data will be interpreted "
                                   "as raw HTML, so it can include an example.")
    allowed_elements = models.CharField("Allowed HTML elements", max_length=255,
                                        help_text="A space separated list of HTML "
                                        "element names.  Use 'row' or 'column' to indicate "
                                        "it can be applied to layout rows or columns ",
                                        default="h1 h2 h3 h4 h5 h6 p blockquote ul li row column")

    column_equiv = models.IntegerField("Column count equivalent", null=True, blank=True,
                                       help_text="For classes designed to be applied to "
                                       "columns only, this is the number of columns this "
                                       "be considered as equivalent too.  This can be "
                                       "useful for generating double width columns etc. "
                                       "within a column layout.")
    def __unicode__(self):
        return self.verbose_name

    class Meta:
        verbose_name = "CSS class"
        verbose_name_plural = "CSS classes"
        ordering = ('verbose_name',)

