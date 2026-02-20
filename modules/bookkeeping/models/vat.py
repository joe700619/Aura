from django.db import models

class VAT(models.Model):
    """Value Added Tax Model"""
    period = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20)

    class Meta:
        db_table = 'bookkeeping_vat'
