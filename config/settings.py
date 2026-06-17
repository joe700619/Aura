"""
Django base settings for Aura.

設定值統一從 .env 讀取（用 django-environ）。
不同環境用 settings_staging.py / settings_production.py 覆蓋。

啟動方式：
- 本機開發：DJANGO_SETTINGS_MODULE=config.settings
- Staging：DJANGO_SETTINGS_MODULE=config.settings_staging
- Production：DJANGO_SETTINGS_MODULE=config.settings_production
"""

from pathlib import Path
from copy import copy
import environ
from django.template import context

# Patch for Python 3.14 compatibility with Django 5.1
def base_context_copy(self):
    duplicate = super(context.BaseContext, self).__new__(self.__class__)
    duplicate.__dict__ = self.__dict__.copy()
    if hasattr(self, 'dicts'):
        duplicate.dicts = self.dicts[:]
    return duplicate

context.BaseContext.__copy__ = base_context_copy

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# 環境變數讀取
# -----------------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    CSRF_TRUSTED_ORIGINS=(list, []),
    DB_PORT=(int, 5432),
    SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
)

env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(env_file)


# -----------------------------------------------------------------------------
# 安全設定
# -----------------------------------------------------------------------------
SECRET_KEY = env('SECRET_KEY', default='django-insecure-DEV-ONLY-DO-NOT-USE-IN-PRODUCTION')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = env('CSRF_TRUSTED_ORIGINS')

# HTTPS / Cookie 安全（production 由 settings_production.py 覆蓋為 True）
SECURE_SSL_REDIRECT = env('SECURE_SSL_REDIRECT')
SESSION_COOKIE_SECURE = env('SESSION_COOKIE_SECURE')
CSRF_COOKIE_SECURE = env('CSRF_COOKIE_SECURE')

# POST 欄位數上限：Django 預設 1000。admin 的 Group 權限表單採 filter_horizontal,
# 每個被勾選的權限會送出一個 POST 欄位;系統 model 數眾多時權限總數遠超過 1000,
# 一次儲存大量權限會觸發 TooManyFieldsSent → 400 Bad Request。故調高上限。
DATA_UPLOAD_MAX_NUMBER_FIELDS = 20000


# -----------------------------------------------------------------------------
# Application definition
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'tailwind',
    'theme',
    'django_browser_reload',
    'widget_tweaks',
    'core',
    'modules.bookkeeping',
    'modules.basic_data',
    'modules.administrative',
    'modules.hr.apps.HrConfig',
    'modules.workflow',
    'modules.system_config',
    'modules.registration',
    'modules.payment',
    'modules.internal_accounting',
    'modules.client_portal',
    'modules.case_management',
    'modules.knowledge_base',
    'modules.public_site',
    'modules.blog',

    # Wagtail CMS
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.contrib.table_block',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail',
    'modelcluster',
    'taggit',

    'import_export',
    'django.contrib.humanize',
    'simple_history',
    'anymail',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.user_permissions',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
# 雙模式：
#   1. Railway / Heroku 等 PaaS：給 DATABASE_URL（postgresql://user:pass@host:port/db）
#   2. 本機 Docker compose：給個別 DB_* 變數
# DATABASE_URL 優先；沒設才用個別變數。
# 用 env() 取字串先檢查；env.db_url() 對「沒設」的回傳行為不同版本不一致，不能直接判斷
_DATABASE_URL = env('DATABASE_URL', default='')
if _DATABASE_URL:
    DATABASES = {'default': env.db_url('DATABASE_URL')}
elif not DEBUG:
    # 正式環境沒拿到 DATABASE_URL → 大聲報錯，而不是默默 fallback 到 localhost
    # （後者會讓 migrate 連到不存在的 DB、healthcheck 失敗，且難以從 log 看出真因）。
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        'DEBUG=False 但未設定 DATABASE_URL。請在 Railway 把 PostgreSQL 服務的 '
        'DATABASE_URL 以 reference variable 連到本服務。'
    )
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default='aura_db'),
            'USER': env('DB_USER', default='postgres'),
            'PASSWORD': env('DB_PASSWORD', default=''),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT'),
        }
    }
# 每個 view 包在 transaction.atomic：任何例外（含 signal 失敗）都 rollback
# 確保「主檔建立 + signal 自動建子檔」保持原子性
DATABASES['default']['ATOMIC_REQUESTS'] = True


# -----------------------------------------------------------------------------
# Cache (Redis)
# Railway 提供 REDIS_URL（已包含密碼），本機 Docker 也用同一個變數名
# -----------------------------------------------------------------------------
REDIS_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/1')
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}


# -----------------------------------------------------------------------------
# Celery
# Railway 提供的 REDIS_URL 可能結尾沒 /db_num（例如 redis://x:6379），
# 因此 broker/result_backend 直接沿用 REDIS_URL，redis 預設會用 db 0
# 本機 Docker 環境 REDIS_URL=redis://redis:6379/1 也仍可正常運作
# -----------------------------------------------------------------------------
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default=REDIS_URL)
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default=CELERY_BROKER_URL)
CELERY_TIMEZONE = 'Asia/Taipei'
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False)
# 預防累積式記憶體洩漏：worker 處理 1000 個 task 後自動重啟
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Celery Beat 定期排程
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    # 每月 1 號凌晨 3 點清除 1 年前的 simple-history 紀錄
    'cleanup-old-history-monthly': {
        'task': 'core.cleanup_old_history',
        'schedule': crontab(hour=3, minute=0, day_of_month=1),
        'kwargs': {'days': 365},
    },
    # 每月 1 號早上 9 點寄送上月勞報繳費提醒（截止日為當月 10 號）
    'send-remuneration-reminders-monthly': {
        'task': 'bookkeeping.send_remuneration_reminders',
        'schedule': crontab(hour=9, minute=0, day_of_month=1),
    },
}


AUTH_USER_MODEL = 'core.User'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Taipei'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# 只在本機 static/ 存在時才加入 STATICFILES_DIRS（避免部署環境 W004）
_STATIC_SRC = BASE_DIR / "static"
STATICFILES_DIRS = [_STATIC_SRC] if _STATIC_SRC.is_dir() else []

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# -----------------------------------------------------------------------------
# Storage backends（Django 4.2+ 統一用 STORAGES dict）
# - default：使用者上傳的 media；本機走 FileSystemStorage，production 走 R2
# - staticfiles：whitenoise（serve compressed static）
# -----------------------------------------------------------------------------
USE_R2 = env.bool('USE_R2', default=False)

if USE_R2:
    # Cloudflare R2（S3 相容）
    AWS_ACCESS_KEY_ID = env('R2_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('R2_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('R2_BUCKET_NAME', default='aura-media-prod')
    AWS_S3_ENDPOINT_URL = env('R2_ENDPOINT_URL')
    AWS_S3_REGION_NAME = 'auto'  # R2 用 auto
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_ADDRESSING_STYLE = 'virtual'
    AWS_DEFAULT_ACL = None  # R2 不支援 ACL
    AWS_S3_FILE_OVERWRITE = False  # 同名檔自動加 hash 後綴，避免覆蓋
    AWS_QUERYSTRING_AUTH = True  # 用 presigned URL 下載
    AWS_QUERYSTRING_EXPIRE = 600  # presigned URL 10 分鐘有效
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }

    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
        },
    }
else:
    # 本機開發：檔案存在 docker volume
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
        },
    }

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

TAILWIND_APP_NAME = 'theme'

INTERNAL_IPS = ['127.0.0.1']


# -----------------------------------------------------------------------------
# Debug Toolbar（僅在 DEBUG=True 啟用）
# -----------------------------------------------------------------------------
if DEBUG:
    try:
        import debug_toolbar  # noqa: F401
        INSTALLED_APPS += ['debug_toolbar']
        # 必須放在 CommonMiddleware 之後、其他 middleware 前面
        MIDDLEWARE.insert(
            MIDDLEWARE.index('django.middleware.common.CommonMiddleware') + 1,
            'debug_toolbar.middleware.DebugToolbarMiddleware',
        )
        # Docker 環境下 client IP 是 docker 內網 IP，需要 callback 判定
        DEBUG_TOOLBAR_CONFIG = {
            'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
            'DISABLE_PANELS': {
                'debug_toolbar.panels.history.HistoryPanel',
                'debug_toolbar.panels.profiling.ProfilingPanel',
                'debug_toolbar.panels.redirects.RedirectsPanel',
            },
        }
    except ImportError:
        # production image 沒裝 dev 套件，跳過
        pass

NPM_BIN_PATH = env('NPM_BIN_PATH', default='npm.cmd')


# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='Aura ERP <noreply@aura-erp.com>')

# Resend（HTTPS API 寄信）— Railway 封鎖對外 SMTP，故正式環境走 API。
# 啟用方式：env 設 EMAIL_BACKEND=anymail.backends.resend.EmailBackend + RESEND_API_KEY，
# 並確保 SystemParameter 的 EMAIL_HOST 為空（有值會讓寄信改走被封鎖的 SMTP）。
ANYMAIL = {
    'RESEND_API_KEY': env('RESEND_API_KEY', default=''),
}


# -----------------------------------------------------------------------------
# Wagtail CMS
# -----------------------------------------------------------------------------
LINE_OA_URL = env('LINE_OA_URL', default='https://lin.ee/RYzygHv')
# 官網諮詢 / 快速登記表單送出時通知事務所的收件信箱（多個用逗號分隔）。
# 主要在 admin「系統參數設定」的 INQUIRY_NOTIFY_EMAIL 設定；這裡的 env 僅作 fallback。
INQUIRY_NOTIFY_EMAIL = env('INQUIRY_NOTIFY_EMAIL', default='')
WAGTAIL_SITE_NAME = '勤信 CMS'
WAGTAILADMIN_BASE_URL = env('WAGTAILADMIN_BASE_URL', default='http://localhost:8000')
WAGTAILDOCS_EXTENSIONS = ['csv', 'docx', 'key', 'odt', 'pdf', 'pptx', 'rtf', 'txt', 'xlsx', 'zip']
TAGGIT_CASE_INSENSITIVE = True


# -----------------------------------------------------------------------------
# Sentry（僅在 SENTRY_DSN 有設時啟用）
# -----------------------------------------------------------------------------
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration(), CeleryIntegration()],
            traces_sample_rate=env.float('SENTRY_TRACES_SAMPLE_RATE', default=0.1),
            send_default_pii=False,  # 不送個資（password、email body 等）
            environment=env('SENTRY_ENVIRONMENT', default='development'),
            release=env('SENTRY_RELEASE', default=None),
        )
    except ImportError:
        pass  # production image 沒裝就靜默


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': env('LOG_LEVEL', default='INFO'),
    },
    'loggers': {
        # 掃描機器人狂打 /.env、/wp-admin、/.git 等路徑會被記成 WARNING(404)。
        # 只拉 level（不設 handler、保留 propagate）：WARNING(404/400) 在產生當下
        # 就被丟掉，ERROR(500) 照樣往上送到 root（dev→console、prod→console+file）。
        'django.request': {
            'level': 'ERROR',
        },
        # 偽造 Host header 的探測（DisallowedHost）同屬背景雜訊，靜音。
        'django.security.DisallowedHost': {
            'level': 'CRITICAL',
        },
    },
}
