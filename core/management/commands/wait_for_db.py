import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    """
    等待 default 資料庫可連線後才返回。

    用途：容器啟動時，web 服務常比 PostgreSQL 早就緒，或 Railway 私有網路
    （*.railway.internal）DNS 需數秒才解析得到。直接 `migrate` 會在這個空窗
    連一次就 crash，導致 gunicorn 不啟動、healthcheck 失敗。
    在 migrate 前先跑這個指令，重試到連得上為止，消除該 race。
    """
    help = '阻塞直到資料庫可連線（含重試），供容器啟動 migrate 前使用。'

    def add_arguments(self, parser):
        parser.add_argument('--timeout', type=int, default=90,
                            help='最長等待秒數，逾時以 exit 1 結束（預設 90）')
        parser.add_argument('--interval', type=float, default=2.0,
                            help='每次重試間隔秒數（預設 2）')

    def handle(self, *args, **options):
        timeout = options['timeout']
        interval = options['interval']
        conn = connections['default']
        deadline = time.monotonic() + timeout
        attempt = 0

        while True:
            attempt += 1
            try:
                conn.ensure_connection()
            except OperationalError as exc:
                conn.close()  # 丟掉壞掉的連線，下次重新建立
                if time.monotonic() >= deadline:
                    self.stderr.write(self.style.ERROR(
                        f'資料庫在 {timeout}s 內仍無法連線（試了 {attempt} 次）：{exc}'
                    ))
                    raise SystemExit(1)
                self.stdout.write(f'資料庫尚未就緒（第 {attempt} 次），{interval}s 後重試…')
                time.sleep(interval)
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'資料庫已就緒（第 {attempt} 次嘗試）。'
                ))
                return
