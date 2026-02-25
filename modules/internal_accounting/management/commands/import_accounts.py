from django.core.management.base import BaseCommand
from modules.internal_accounting.models import Account

class Command(BaseCommand):
    help = 'Import initial accounting codes'

    def handle(self, *args, **options):
        accounts = [
            ('1110', '現金', Account.Category.ASSET),
            ('111401', '國泰世華', Account.Category.ASSET),
            ('111402', '上海商銀', Account.Category.ASSET),
            ('111403', '綠界', Account.Category.ASSET),
            ('1123', '應收帳款', Account.Category.ASSET),
            ('1124', '應收票據', Account.Category.ASSET),
            ('1140', '預付款項', Account.Category.ASSET),
            ('1149', '扣繳稅款', Account.Category.ASSET),
            ('2121', '應付費用', Account.Category.LIABILITY),
            ('2123', '應付帳款', Account.Category.LIABILITY),
            ('2190', '預收款項', Account.Category.LIABILITY),
            ('2192', '股東往來', Account.Category.LIABILITY),
            ('3000', '股本', Account.Category.EQUITY),
            ('3100', '保留盈餘', Account.Category.EQUITY),
            ('400001', '簽證收入', Account.Category.REVENUE),
            ('400002', '記帳收入', Account.Category.REVENUE),
            ('400003', '登記收入', Account.Category.REVENUE),
            ('6100', '薪資費用', Account.Category.EXPENSE),
        ]

        for code, name, category in accounts:
            account, created = Account.objects.get_or_create(
                code=code,
                defaults={'name': name, 'category': category}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created account {code} {name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Account {code} {name} already exists'))
