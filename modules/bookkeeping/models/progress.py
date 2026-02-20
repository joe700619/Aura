from django.db import models

class Progress(models.Model):
    """Progress Model"""
    description = models.CharField(max_length=255)
    percentage = models.IntegerField()

    class Meta:
        db_table = 'bookkeeping_progress'
