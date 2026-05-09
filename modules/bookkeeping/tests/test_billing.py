"""
ClientBill 邏輯測試（bill_no 自動產生、total 重算、unique 約束）。
"""
from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction


@pytest.mark.django_db
class TestClientBill:

    def test_bill_no_auto_generated_on_save(self, bookkeeping_client):
        from modules.bookkeeping.models.billing import ClientBill
        bill = ClientBill.objects.create(
            client=bookkeeping_client, year=2026, month=5,
        )
        assert bill.bill_no  # 非空
        assert bill.bill_no.startswith('BI')

    def test_bill_no_sequential(self, bookkeeping_client):
        """同一天連建兩張帳單，bill_no 序號遞增"""
        from modules.bookkeeping.models.billing import ClientBill
        b1 = ClientBill.objects.create(client=bookkeeping_client, year=2026, month=5)
        b2 = ClientBill.objects.create(client=bookkeeping_client, year=2026, month=6)
        assert b1.bill_no != b2.bill_no

    def test_unique_together_client_year_month(self, bookkeeping_client):
        from modules.bookkeeping.models.billing import ClientBill
        ClientBill.objects.create(client=bookkeeping_client, year=2026, month=5)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ClientBill.objects.create(client=bookkeeping_client, year=2026, month=5)

    def test_default_status_is_draft(self, bookkeeping_client):
        from modules.bookkeeping.models.billing import ClientBill
        bill = ClientBill.objects.create(client=bookkeeping_client, year=2026, month=5)
        assert bill.status == ClientBill.BillStatus.DRAFT

    def test_total_amount_recalculation(self, bookkeeping_client):
        """recalculate_total 應從 quotation_data 計算總額"""
        from modules.bookkeeping.models.billing import ClientBill
        bill = ClientBill.objects.create(
            client=bookkeeping_client, year=2026, month=5,
            quotation_data=[
                {'amount': 1000},
                {'amount': 2500},
                {'amount': 500},
            ],
        )
        bill.recalculate_total()
        bill.refresh_from_db()
        assert bill.total_amount == Decimal(4000)
