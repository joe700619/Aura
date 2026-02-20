from django.db import models

class Withholding(models.Model):
    """Withholding Tax Model"""
    name = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        db_table = 'bookkeeping_withholding'
