from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class GroupInvoice(BaseModel):
    """統購發票明細"""

    class InvoiceType(models.TextChoices):
        TWO_COPY = 'two_copy', '二聯'
        TWO_COPY_SUB = 'two_copy_sub', '二聯副'
        THREE_COPY = 'three_copy', '三聯'
        THREE_COPY_SUB = 'three_copy_sub', '三聯副'
        SPECIAL = 'special', '特種'
        TWO_CASHIER = 'two_cashier', '二收銀'
        THREE_CASHIER = 'three_cashier', '三收銀'
        THREE_CASHIER_SUB = 'three_cashier_sub', '三收銀副'

    client = models.ForeignKey(
        'bookkeeping.BookkeepingClient',
        on_delete=models.CASCADE,
        related_name='group_invoices',
        verbose_name=_('記帳客戶'),
    )
    invoice_type = models.CharField(
        _('發票類別'), max_length=20,
        choices=InvoiceType.choices,
    )
    quantity = models.PositiveIntegerField(_('數量'), default=0)

    class Meta:
        verbose_name = _('統購發票')
        verbose_name_plural = _('統購發票')
        ordering = ['invoice_type']
        unique_together = [['client', 'invoice_type']]

    def __str__(self):
        return f"{self.client.name} - {self.get_invoice_type_display()}"
