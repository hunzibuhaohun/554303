"""
WSGI配置 - 用于生产环境部署
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_checkin.settings.prod')

application = get_wsgi_application()
