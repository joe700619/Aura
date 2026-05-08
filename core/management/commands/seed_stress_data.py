"""
壓力測試資料生成器。

用途：上線前批次 3，灌入接近正式運作規模的資料量，驗證
列表/搜尋/報表頁在大資料量下的效能。

特性：
- 用 bulk_create 加速（10x+），跳過 signal 與 history（壓測不在意這些）
- 可指定 scale 參數調整資料量
- 安全保護：僅 DEBUG=True 才能執行（避免誤灌正式環境）
- 預先生成唯一 tax_id / username 避免衝突
- 灌完印出統計數字

範例：
    docker-compose exec web python manage.py seed_stress_data
    docker-compose exec web python manage.py seed_stress_data --scale 0.1   # 10% 規模快速測試
    docker-compose exec web python manage.py seed_stress_data --clear        # 先清舊測試資料
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone


SURNAMES = ['王', '李', '張', '劉', '陳', '楊', '黃', '趙', '吳', '周', '徐', '孫', '馬', '朱', '胡', '郭', '何', '高', '林', '羅']
GIVEN = ['俊', '明', '偉', '強', '磊', '麗', '芳', '娜', '靜', '敏', '豪', '宇', '欣', '婷', '志', '建', '文', '彥', '冠', '柏']
COMPANY_SUFFIX = ['有限公司', '股份有限公司', '企業社', '行', '工坊', '事業有限公司']


def fake_name():
    return random.choice(SURNAMES) + random.choice(GIVEN) + random.choice(GIVEN)


def fake_company():
    return random.choice(SURNAMES) + random.choice(GIVEN) + random.choice(COMPANY_SUFFIX)


def fake_phone():
    return f'09{random.randint(10000000, 99999999)}'


def fake_email(idx):
    return f'test{idx}@example.com'


def fake_tax_id(idx):
    """產生 8 碼數字（允許重複時不檢查 checksum）"""
    return f'{10000000 + idx:08d}'


def daterange_random(start_year=2020, end_year=2026):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, delta_days))


class Command(BaseCommand):
    help = '灌入壓力測試資料（5K 客戶 / 50K 帳單 / 20K 案件等規模）'

    def add_arguments(self, parser):
        parser.add_argument('--scale', type=float, default=1.0,
                            help='規模倍數，1.0 = 完整 5K 客戶（預設）；0.1 = 500 客戶快速測試')
        parser.add_argument('--clear', action='store_true',
                            help='灌之前先刪除既有測試資料（tax_id 開頭 1 開始的）')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('僅允許在 DEBUG=True 的環境執行壓測 seed')

        scale = options['scale']
        clear = options['clear']

        # 規模設定
        n_customers = int(5000 * scale)
        n_bills = int(50000 * scale)
        n_cases = int(20000 * scale)
        n_inquiries = int(10000 * scale)
        n_receivables = int(30000 * scale)

        self.stdout.write(self.style.WARNING(
            f'\n=== 即將灌入壓測資料（scale={scale}）===\n'
            f'  Customer × {n_customers}\n'
            f'  BookkeepingClient × {n_customers}\n'
            f'  ClientBill × {n_bills}\n'
            f'  Case × {n_cases}\n'
            f'  Inquiry × {n_inquiries}\n'
            f'  Receivable × {n_receivables}\n'
        ))

        if clear:
            self._clear_test_data()

        random.seed(42)  # 可重現

        with transaction.atomic():
            customer_ids = self._seed_customers(n_customers)
            client_ids = self._seed_bookkeeping_clients(n_customers, customer_ids)
            self._seed_bills(n_bills, client_ids)
            self._seed_cases(n_cases)
            self._seed_inquiries(n_inquiries)
            self._seed_receivables(n_receivables)

        self.stdout.write(self.style.SUCCESS('\n✓ 壓測資料灌完'))
        self._print_stats()

    # =========================================================================
    # Clear
    # =========================================================================
    def _clear_test_data(self):
        from modules.basic_data.models import Customer
        from modules.bookkeeping.models import BookkeepingClient
        from modules.bookkeeping.models.billing import ClientBill
        from modules.case_management.models import Case, Inquiry
        from modules.internal_accounting.models.receivable import Receivable

        self.stdout.write('清除舊測試資料...')
        # tax_id 範圍 10000000 ~ 19999999 是測試資料
        BookkeepingClient.objects.filter(tax_id__startswith='1').delete()
        Customer.objects.filter(tax_id__startswith='1').delete()
        ClientBill.objects.filter(notes='[stress-test]').delete()
        Case.objects.filter(summary='[stress-test]').delete()
        Inquiry.objects.filter(note='[stress-test]').delete()
        Receivable.objects.filter(remarks='[stress-test]').delete()
        self.stdout.write(self.style.SUCCESS('  清除完成\n'))

    # =========================================================================
    # Customer
    # =========================================================================
    def _seed_customers(self, n):
        from modules.basic_data.models import Customer
        self.stdout.write(f'灌 Customer × {n} ...', ending='')
        objs = [
            Customer(
                tax_id=fake_tax_id(i),
                name=fake_company(),
                email=fake_email(i),
                phone=fake_phone(),
                mobile=fake_phone(),
                contact_person=fake_name(),
                source='ESTABLISHED',
            )
            for i in range(n)
        ]
        created = Customer.objects.bulk_create(objs, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f' {len(created)}'))
        return [c.pk for c in created]

    # =========================================================================
    # BookkeepingClient
    # =========================================================================
    def _seed_bookkeeping_clients(self, n, customer_ids):
        from modules.bookkeeping.models import BookkeepingClient
        self.stdout.write(f'灌 BookkeepingClient × {n} ...', ending='')

        acceptance_choices = ['active'] * 8 + ['suspended'] * 1 + ['transferred'] * 1
        billing_choices = ['billing'] * 9 + ['stopped'] * 1
        service_choices = ['vat_business', 'mixed_direct', 'mixed_ratio', 'investment', 'professional']

        objs = [
            BookkeepingClient(
                tax_id=fake_tax_id(i),
                name=fake_company(),
                phone=fake_phone(),
                mobile=fake_phone(),
                email=fake_email(i),
                acceptance_status=random.choice(acceptance_choices),
                billing_status=random.choice(billing_choices),
                service_type=random.choice(service_choices),
                customer_id=customer_ids[i],
                contact_person=fake_name(),
                contact_date=daterange_random(),
            )
            for i in range(n)
        ]
        # 不用 ignore_conflicts，PostgreSQL 才能回傳 pk
        created = BookkeepingClient.objects.bulk_create(objs, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f' {len(created)}'))
        return [c.pk for c in created]

    # =========================================================================
    # ClientBill
    # =========================================================================
    def _seed_bills(self, n, client_ids):
        from modules.bookkeeping.models.billing import ClientBill
        self.stdout.write(f'灌 ClientBill × {n} ...', ending='')

        if not client_ids:
            self.stdout.write(self.style.WARNING(' 跳過（沒客戶）'))
            return

        status_choices = ['draft', 'sent', 'paid', 'overdue']
        objs = []
        seen = set()  # (client, year, month) unique_together
        for i in range(n):
            client_id = random.choice(client_ids)
            year = random.randint(2023, 2026)
            month = random.randint(1, 12)
            key = (client_id, year, month)
            if key in seen:
                # 換一組
                continue
            seen.add(key)
            objs.append(ClientBill(
                bill_no=f'BI-STRESS-{i:08d}',
                client_id=client_id,
                year=year,
                month=month,
                bill_date=daterange_random(year, year),
                status=random.choice(status_choices),
                total_amount=Decimal(random.randint(3000, 50000)),
                notes='[stress-test]',
            ))
        created = ClientBill.objects.bulk_create(objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f' {len(created)}'))

    # =========================================================================
    # Case
    # =========================================================================
    def _seed_cases(self, n):
        from modules.case_management.models import Case
        from core.models import User
        self.stdout.write(f'灌 Case × {n} ...', ending='')

        # 取一個 superuser 當預設 owner（避免 owner_id NULL 約束）
        owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if owner is None:
            self.stdout.write(self.style.WARNING(' 跳過（無任何 User，無法當 owner）'))
            return

        category_choices = ['consult', 'task', 'incident']
        status_choices = ['open', 'in_progress', 'pending_reply', 'closed']
        priority_choices = ['low', 'normal', 'high', 'urgent']
        source_choices = ['internal', 'email', 'line', 'phone']

        objs = [
            Case(
                title=f'測試案件 #{i} {fake_company()}',
                summary='[stress-test]',
                category=random.choice(category_choices),
                status=random.choice(status_choices),
                priority=random.choice(priority_choices),
                source=random.choice(source_choices),
                owner_id=owner.pk,
                external_contact_name=fake_name(),
                external_contact_email=fake_email(i),
                external_contact_phone=fake_phone(),
                last_activity_at=timezone.now() - timedelta(days=random.randint(0, 365)),
            )
            for i in range(n)
        ]
        created = Case.objects.bulk_create(objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f' {len(created)}'))

    # =========================================================================
    # Inquiry
    # =========================================================================
    def _seed_inquiries(self, n):
        from modules.case_management.models import Inquiry
        self.stdout.write(f'灌 Inquiry × {n} ...', ending='')

        status_choices = ['new', 'contacted', 'won', 'lost']
        source_choices = ['homepage', 'line', 'phone', 'referral']
        stage_choices = ['startup', 'growth', 'mature']

        objs = [
            Inquiry(
                name=fake_name(),
                email=fake_email(i),
                phone=fake_phone(),
                company=fake_company(),
                stage=random.choice(stage_choices),
                message='[stress-test]',
                source=random.choice(source_choices),
                status=random.choice(status_choices),
                note='[stress-test]',
            )
            for i in range(n)
        ]
        created = Inquiry.objects.bulk_create(objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f' {len(created)}'))

    # =========================================================================
    # Receivable
    # =========================================================================
    def _seed_receivables(self, n):
        from modules.internal_accounting.models.receivable import Receivable
        self.stdout.write(f'灌 Receivable × {n} ...', ending='')

        objs = [
            Receivable(
                receivable_no=f'AR-STRESS-{i:08d}',
                date=daterange_random(),
                company_name=fake_company(),
                unified_business_no=fake_tax_id(i),
                main_contact=fake_name(),
                phone=fake_phone(),
                mobile=fake_phone(),
                email=fake_email(i),
                remarks='[stress-test]',
            )
            for i in range(n)
        ]
        created = Receivable.objects.bulk_create(objs, batch_size=1000)
        self.stdout.write(self.style.SUCCESS(f' {len(created)}'))

    # =========================================================================
    # Stats
    # =========================================================================
    def _print_stats(self):
        from modules.basic_data.models import Customer
        from modules.bookkeeping.models import BookkeepingClient
        from modules.bookkeeping.models.billing import ClientBill
        from modules.case_management.models import Case, Inquiry
        from modules.internal_accounting.models.receivable import Receivable

        self.stdout.write('\n=== 目前資料表筆數 ===')
        for m in [Customer, BookkeepingClient, ClientBill, Case, Inquiry, Receivable]:
            self.stdout.write(f'  {m.__name__}: {m.objects.count():,}')
