from django.db import models

class IncomeTax(models.Model):
    """Income Tax Model"""
    year = models.IntegerField()
    taxable_income = models.DecimalField(max_digits=15, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'bookkeeping_income_tax'
