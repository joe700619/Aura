"""
驗證批次 1 的 signal 集中與 ATOMIC_REQUESTS 行為。

關鍵流程：BookkeepingClient 建立 → 自動建以下子檔
- BusinessRegistration
- TaxFilingSetting (依 service_type 決定 401/403)
- IncomeTaxSetting
- BookkeepingSetting
- 對應 user (依 tax_id)
"""
import pytest
from django.db import IntegrityError, transaction


@pytest.mark.django_db
class TestBookkeepingClientSignals:

    def test_creating_client_creates_business_registration(self, customer):
        from modules.bookkeeping.models import BookkeepingClient
        from modules.bookkeeping.models.business_registration import BusinessRegistration

        client = BookkeepingClient.objects.create(
            tax_id='10000001', name='A', customer=customer,
            service_type='vat_business',
        )
        assert BusinessRegistration.objects.filter(client=client).exists()

    def test_vat_business_creates_form_401(self, customer):
        from modules.bookkeeping.models import BookkeepingClient
        from modules.bookkeeping.models.business_tax import TaxFilingSetting

        client = BookkeepingClient.objects.create(
            tax_id='10000002', name='B', customer=customer,
            service_type='vat_business',
        )
        setting = TaxFilingSetting.objects.get(client=client)
        assert setting.form_type == TaxFilingSetting.FormType.FORM_401

    def test_mixed_direct_creates_form_403(self, customer):
        from modules.bookkeeping.models import BookkeepingClient
        from modules.bookkeeping.models.business_tax import TaxFilingSetting

        client = BookkeepingClient.objects.create(
            tax_id='10000003', name='C', customer=customer,
            service_type='mixed_direct',
        )
        setting = TaxFilingSetting.objects.get(client=client)
        assert setting.form_type == TaxFilingSetting.FormType.FORM_403

    def test_investment_does_not_create_tax_filing_setting(self, customer):
        from modules.bookkeeping.models import BookkeepingClient
        from modules.bookkeeping.models.business_tax import TaxFilingSetting

        client = BookkeepingClient.objects.create(
            tax_id='10000004', name='D', customer=customer,
            service_type='investment',
        )
        # 投資公司不需要報營業稅 → 不建 TaxFilingSetting
        assert not TaxFilingSetting.objects.filter(client=client).exists()

    def test_creating_client_creates_income_tax_setting(self, customer):
        from modules.bookkeeping.models import BookkeepingClient
        from modules.bookkeeping.models.income_tax import IncomeTaxSetting

        client = BookkeepingClient.objects.create(
            tax_id='10000005', name='E', customer=customer,
            service_type='vat_business',
        )
        assert IncomeTaxSetting.objects.filter(client=client).exists()

    def test_creating_client_creates_bookkeeping_setting(self, customer):
        from modules.bookkeeping.models import BookkeepingClient
        from modules.bookkeeping.models.progress import BookkeepingSetting

        client = BookkeepingClient.objects.create(
            tax_id='10000006', name='F', customer=customer,
            service_type='vat_business',
        )
        assert BookkeepingSetting.objects.filter(client=client).exists()

    def test_creating_client_with_tax_id_creates_portal_user(self, customer):
        from django.contrib.auth import get_user_model
        from modules.bookkeeping.models import BookkeepingClient

        BookkeepingClient.objects.create(
            tax_id='10000007', name='G', customer=customer,
            service_type='vat_business', email='g@example.com',
        )
        User = get_user_model()
        user = User.objects.filter(username='10000007').first()
        assert user is not None
        assert user.role == 'EXTERNAL'
        assert user.email == 'g@example.com'

    def test_signals_idempotent_on_resave(self, customer):
        """重新 save 不會重複建立子檔（用 get_or_create 保證 idempotent）"""
        from modules.bookkeeping.models import BookkeepingClient
        from modules.bookkeeping.models.business_registration import BusinessRegistration

        client = BookkeepingClient.objects.create(
            tax_id='10000008', name='H', customer=customer,
            service_type='vat_business',
        )
        client.save()
        client.save()  # 重存 3 次

        assert BusinessRegistration.objects.filter(client=client).count() == 1


# =============================================================================
# IncomeTaxYear → 5 個子項目自動建立
# =============================================================================
@pytest.mark.django_db
class TestIncomeTaxYearSignal:

    def test_year_creates_five_sub_items(self, bookkeeping_client):
        from modules.bookkeeping.models.income_tax import (
            IncomeTaxYear, ProvisionalTax, WithholdingTax, DividendTax, IncomeTaxFiling,
        )
        from modules.bookkeeping.models.income_tax_media import IncomeTaxMediaData

        year = IncomeTaxYear.objects.create(client=bookkeeping_client, year=114)

        assert ProvisionalTax.objects.filter(year_record=year).exists()
        assert WithholdingTax.objects.filter(year_record=year).exists()
        assert DividendTax.objects.filter(year_record=year).exists()
        assert IncomeTaxFiling.objects.filter(year_record=year).exists()
        assert IncomeTaxMediaData.objects.filter(year_record=year).exists()
