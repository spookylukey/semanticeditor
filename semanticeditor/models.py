from django.db import models

class CssClass(models.Model):
    class_name = models.CharField("CSS class name", max_length=255, unique=True)
    description = models.CharField("Description", max_length=255, blank=True)

    def __unicode__(self):
        return self.class_name

    class Meta:
        verbose_name = "CSS class"
        verbose_name_plural = "CSS classes"

