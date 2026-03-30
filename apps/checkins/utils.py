
"""
打卡工具函数 - 校园打卡平台
"""
import math

import requests
from django.conf import settings
from datetime import timedelta
from django.utils import timezone

from .models import CheckIn, PointRecord


def calculate_distance(lat1, lng1, lat2, lng2):
    """使用 Haversine 公式计算两点间距离（米）"""
    radius = 6371000
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    delta_lat = math.radians(float(lat2) - float(lat1))
    delta_lng = math.radians(float(lng2) - float(lng1))

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def verify_location(user_lat, user_lng, activity_lat, activity_lng, radius=500):
    if user_lat in [None, ''] or user_lng in [None, ''] or activity_lat in [None, ''] or activity_lng in [None, '']:
        return False, '位置信息不完整'

    distance = calculate_distance(user_lat, user_lng, activity_lat, activity_lng)
    if distance <= radius:
        return True, f'距离活动位置 {distance:.0f} 米，验证通过'
    return False, f'距离活动位置 {distance:.0f} 米，超出允许范围 {radius} 米'


def get_address_from_coordinates(lat, lng):
    if not settings.AMAP_KEY:
        return f'{lat},{lng}'

    url = 'https://restapi.amap.com/v3/geocode/regeo'
    params = {
        'key': settings.AMAP_KEY,
        'location': f'{lng},{lat}',
        'extensions': 'base',
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data.get('status') == '1':
            return data['regeocode']['formatted_address']
    except Exception:
        pass
    return f'{lat},{lng}'


def calculate_continuous_days(user, activity=None):
    """
    统计连续打卡天数，只计算已通过审核的记录。
    支持按单个活动统计，也支持全站统计。
    """
    filters = {'user': user, 'status': 'approved'}
    if activity is not None:
        filters['activity'] = activity

    checkin_dates = list(
        CheckIn.objects.filter(**filters)
        .values_list('check_in_date', flat=True)
        .distinct()
        .order_by('-check_in_date')
    )
    if not checkin_dates:
        return 0

    today = timezone.localdate()
    latest = checkin_dates[0]

    if latest != today and (today - latest).days > 1:
        return 0

    date_set = set(checkin_dates)
    cursor = latest
    continuous_days = 0
    while cursor in date_set:
        continuous_days += 1
        cursor = cursor - timedelta(days=1)

    return continuous_days


def award_points(user, activity, streak_days=1, related_checkin=None):
    """
    发放积分规则：
    - 基础分：活动积分
    - 连续奖励：每满 7 天额外 +5 分，上限 +20
    """
    base_points = int(getattr(activity, 'points', 10) or 10)
    streak_days = int(streak_days or 0)
    bonus = min((streak_days // 7) * 5, 20)
    final_points = base_points + bonus

    user.points += final_points
    user.total_checkins += 1
    user.update_streak()
    user.save(update_fields=['points', 'total_checkins', 'streak_days', 'longest_streak', 'last_checkin_date'])

    PointRecord.objects.create(
        user=user,
        points=final_points,
        reason=f'打卡奖励 - {activity.title}',
        related_checkin=related_checkin,
    )
    return final_points
