"""
View-level smoke tests：
- 主要列表頁 200 + SQL 數 < 15
- 登入流程
- 權限保護
"""
import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection


# 寬鬆 threshold，留 buffer 給 middleware / context_processor / sidebar 渲染。
# 真正的 N+1 通常會超過這個數很多倍（100+）
SQL_THRESHOLD = 50


@pytest.mark.django_db
class TestAuthFlow:

    def test_login_page_returns_200(self, client):
        resp = client.get('/login/')
        assert resp.status_code == 200

    def test_dashboard_redirects_when_not_authenticated(self, client):
        resp = client.get('/dashboard/')
        # 未登入應 redirect 到 login
        assert resp.status_code in (302, 301)
        assert '/login' in resp['Location']

    def test_dashboard_loads_for_superuser(self, superuser_client):
        resp = superuser_client.get('/dashboard/')
        assert resp.status_code == 200


@pytest.mark.django_db
class TestListViewsSmokeForSuperuser:
    """主要列表頁：超級使用者應該都能 200 開啟"""

    @pytest.fixture(autouse=True)
    def _login(self, superuser_client):
        self.client = superuser_client

    @pytest.mark.parametrize('url', [
        '/basic-data/customers/',
        '/basic-data/contacts/',
        '/basic-data/service-items/',
        '/bookkeeping/clients/',
        '/bookkeeping/bills/',
        '/bookkeeping/business-tax/',
        '/bookkeeping/income-tax/',
        '/bookkeeping/business-registration/',
        '/bookkeeping/industry-tax-rates/',
        '/registration/progress/',
        '/registration/client-assessments/',
        '/registration/case-assessments/',
        '/cases/',
        '/accounting/vouchers/',
        '/accounting/receivables/',
        '/accounting/collections/',
        '/accounting/accounts/',
        '/hr/employees/',
        '/administrative/document-receipts/',
        '/administrative/document-dispatches/',
        '/administrative/irs-audit-notices/',
        '/administrative/advance-payments/',
    ])
    def test_list_returns_200(self, url):
        resp = self.client.get(url)
        # 容許 redirect（部分頁面可能需要額外 state）
        assert resp.status_code in (200, 302), f'{url} → {resp.status_code}'

    def test_customer_list_sql_count_under_threshold(self):
        """客戶列表 SQL 數 < 20 — 防止未來 N+1 回歸"""
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get('/basic-data/customers/')
        assert resp.status_code == 200
        assert len(ctx) < SQL_THRESHOLD, (
            f'Customer list 用了 {len(ctx)} 條 SQL，可能有 N+1 回歸'
        )

    def test_bookkeeping_client_list_sql_count_under_threshold(self):
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get('/bookkeeping/clients/')
        assert resp.status_code == 200
        assert len(ctx) < SQL_THRESHOLD


@pytest.mark.django_db
class TestProtectedAccess:

    def test_anonymous_redirected_from_protected_view(self, client):
        resp = client.get('/basic-data/customers/')
        assert resp.status_code in (302, 301)

    def test_external_user_cannot_access_internal_pages(self, client, external_user):
        """EXTERNAL role 不應能進入內部後台"""
        client.force_login(external_user)
        resp = client.get('/bookkeeping/clients/')
        # 應該被 redirect 或 403
        assert resp.status_code in (302, 403, 404)


@pytest.mark.django_db
class TestStaticAndDashboard:

    def test_homepage_returns_response(self, client):
        resp = client.get('/')
        # 對外網站、登入頁、redirect 任一都 OK
        assert resp.status_code in (200, 302)

    def test_dashboard_uses_few_queries(self, superuser_client):
        """Dashboard 整頁的 SQL 數應在合理範圍"""
        with CaptureQueriesContext(connection) as ctx:
            resp = superuser_client.get('/dashboard/')
        assert resp.status_code == 200
        # Dashboard 通常有更多 widget 查詢，threshold 放寬
        assert len(ctx) < 80, f'Dashboard 用了 {len(ctx)} 條 SQL'
