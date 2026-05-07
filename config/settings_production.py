"""
Production 設定：最嚴格的安全設定。
"""
from .settings import *  # noqa

DEBUG = False

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# Production 寫檔記錄 ERROR（自動建立 logs 目錄）
_LOG_DIR = BASE_DIR / 'logs'
_LOG_DIR.mkdir(exist_ok=True)

LOGGING['handlers']['file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': _LOG_DIR / 'aura.log',
    'maxBytes': 10 * 1024 * 1024,  # 10MB
    'backupCount': 10,
    'formatter': 'verbose',
    'level': 'ERROR',
}
LOGGING['root']['handlers'] = ['console', 'file']
