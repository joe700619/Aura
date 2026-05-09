"""
Customer / Contact model 行為驗證。
"""
import pytest


@pytest.mark.django_db
class TestCustomer:

    def test_create_customer(self):
        from modules.basic_data.models import Customer
        c = Customer.objects.create(tax_id='99999999', name='ABC 公司')
        assert c.pk is not None
        assert str(c) == 'ABC 公司'

    def test_customer_history_recorded(self):
        """BaseModel 帶 HistoricalRecords，存檔後應有 history 紀錄"""
        from modules.basic_data.models import Customer
        c = Customer.objects.create(tax_id='99999998', name='初版名稱')
        c.name = '更名後'
        c.save()
        # 至少 2 筆 history（建立 + 更新）
        assert c.history.count() >= 2

    def test_index_on_searchable_fields(self):
        """確認批次 2 加的 db_index 真的在 schema 上"""
        from modules.basic_data.models import Customer
        # Django Meta API 可查 field.db_index
        tax_id_field = Customer._meta.get_field('tax_id')
        name_field = Customer._meta.get_field('name')
        assert tax_id_field.db_index is True
        assert name_field.db_index is True
