"""
啟用 pgvector extension。

knowledge_base.0001_initial 用到 vector(768) 欄位，需要先啟用。
原本透過 docker/db-init/01-extensions.sql 啟用，但該腳本只在容器初始化時跑，
test DB（pytest-django 動態建立）不會跑到，故補一支 migration 確保所有 DB 都啟用。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_scheduledjob'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS vector',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
