from django.db import models


class Update(models.Model):

    title = models.CharField(
        max_length=200, null=False, blank=False, unique=False
    )
    date = models.DateField(null=False, blank=False)
    description = models.TextField(null=True, blank=True)


