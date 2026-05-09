"""
專案級 pytest fixtures。
任何測試模組都能直接用以下 fixture：

- user, superuser, external_user
- auth_client（已登入的 Django test client）
- customer, bookkeeping_client（資料 fixture）
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import Client


User = get_user_model()


# =============================================================================
# Celery: 測試時同步執行（必須直接更新 celery app 的 conf，而不只是 Django settings）
# =============================================================================
@pytest.fixture(autouse=True)
def _celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    from config.celery import app as celery_app
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


# =============================================================================
# 測試時不要跑 debug_toolbar middleware（會撞到 djdt namespace 未註冊）
# 注意：不能動 INSTALLED_APPS，會觸發 wagtail 重複註冊 snippet
# =============================================================================
@pytest.fixture(autouse=True)
def _disable_debug_toolbar(settings):
    settings.MIDDLEWARE = [m for m in settings.MIDDLEWARE if 'debug_toolbar' not in m]


# =============================================================================
# 用戶
# =============================================================================
@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='alice', password='pass1234', email='alice@example.com'
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username='admin', password='admin1234', email='admin@example.com'
    )


@pytest.fixture
def external_user(db):
    return User.objects.create_user(
        username='ext_user', password='pass1234', email='ext@example.com',
        role='EXTERNAL',
    )


# =============================================================================
# 已登入的 client
# =============================================================================
@pytest.fixture
def client():
    return Client()


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def superuser_client(client, superuser):
    client.force_login(superuser)
    return client


# =============================================================================
# 業務資料 fixture
# =============================================================================
@pytest.fixture
def customer(db):
    from modules.basic_data.models import Customer
    return Customer.objects.create(
        tax_id='12345678',
        name='測試客戶有限公司',
        email='customer@example.com',
        phone='0912345678',
    )


@pytest.fixture
def bookkeeping_client(db, customer):
    """建立 BookkeepingClient（會觸發 signal 自動建子檔）"""
    from modules.bookkeeping.models import BookkeepingClient
    return BookkeepingClient.objects.create(
        tax_id='12345678',
        name='測試記帳客戶',
        customer=customer,
        acceptance_status='active',
        billing_status='billing',
        service_type='vat_business',
    )
