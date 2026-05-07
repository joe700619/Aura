"""
Staging 設定：模擬 production 但保留部分 debug 能力。
壓力測試、上線前驗證使用。
"""
from .settings import *  # noqa

DEBUG = False

# Staging 必須走 HTTPS（如果有 reverse proxy）
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600  # staging 用較短 HSTS，避免測試時被卡
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
