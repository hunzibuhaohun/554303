"""
API模块URL配置 - 校园打卡平台
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.views import UserViewSet
from apps.activities.views import ActivityViewSet, ActivityRegistrationViewSet
from apps.checkins.views import CheckInViewSet
from apps.social.views import MomentViewSet

app_name = 'api'

# 创建路由器
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'activities', ActivityViewSet, basename='activity')
router.register(r'registrations', ActivityRegistrationViewSet, basename='registration')
router.register(r'checkins', CheckInViewSet, basename='checkin')
router.register(r'moments', MomentViewSet, basename='moment')

urlpatterns = [
    # JWT认证
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 视图集路由
    path('', include(router.urls)),
]