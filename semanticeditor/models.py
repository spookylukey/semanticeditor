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

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = "CSS class"
        verbose_name_plural = "CSS classes"

