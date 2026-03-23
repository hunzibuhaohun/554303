"""
打卡工具函数 - 校园打卡平台
"""
import math
import requests
from django.conf import settings
from django.utils import timezone
from .models import CheckIn, PointRecord  # 导入需要的模型（确保路径正确）


def calculate_distance(lat1, lng1, lat2, lng2):
    """
    使用Haversine公式计算两点间距离（米）
    """
    R = 6371000  # 地球半径（米）

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def verify_location(user_lat, user_lng, activity_lat, activity_lng, radius=500):
    """
    验证用户位置是否在活动允许范围内

    Args:
        user_lat: 用户纬度
        user_lng: 用户经度
        activity_lat: 活动纬度
        activity_lng: 活动经度
        radius: 允许范围（米）

    Returns:
        (bool, str): (是否通过, 提示信息)
    """
    if not all([user_lat, user_lng, activity_lat, activity_lng]):
        return False, "位置信息不完整"

    distance = calculate_distance(
        float(user_lat), float(user_lng),
        float(activity_lat), float(activity_lng)
    )

    if distance <= radius:
        return True, f"距离活动位置{distance:.0f}米，验证通过"
    else:
        return False, f"距离活动位置{distance:.0f}米，超出允许范围{radius}米"


def get_address_from_coordinates(lat, lng):
    """
    使用高德地图API将坐标转换为地址
    """
    if not settings.AMAP_KEY:
        return f"{lat},{lng}"

    url = "https://restapi.amap.com/v3/geocode/regeo"
    params = {
        'key': settings.AMAP_KEY,
        'location': f"{lng},{lat}",
        'extensions': 'base',
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data.get('status') == '1':
            return data['regeocode']['formatted_address']
    except Exception as e:
        # 捕获异常但不中断程序，仅打印日志（生产环境建议用logging）
        print(f"高德地图API调用失败: {str(e)}")

    return f"{lat},{lng}"


def calculate_continuous_days(user, activity=None):
    """
    计算用户连续打卡天数（支持按活动筛选）

    Args:
        user: 用户对象（request.user）
        activity: 可选，活动对象，仅计算该活动的连续打卡

    Returns:
        int: 连续打卡天数
    """
    # 构建查询条件：当前用户的有效打卡记录，按时间倒序排列
    query_kwargs = {'user': user, 'is_valid': True}  # 假设CheckIn模型有is_valid字段标记有效打卡
    if activity:
        query_kwargs['activity'] = activity

    checkins = CheckIn.objects.filter(**query_kwargs).order_by('-checkin_time')
    if not checkins:
        return 0  # 无打卡记录，连续天数为0

    continuous_days = 1
    today = timezone.now().date()
    last_checkin_date = checkins[0].checkin_time.date()

    # 检查最新打卡是否是今天/昨天（处理跨天逻辑）
    if last_checkin_date != today and (today - last_checkin_date).days > 1:
        return 0

    # 遍历历史打卡记录，计算连续天数
    for checkin in checkins[1:]:
        current_date = checkin.checkin_time.date()
        # 相邻两条记录间隔1天则连续，否则中断
        if (last_checkin_date - current_date).days == 1:
            continuous_days += 1
            last_checkin_date = current_date
        else:
            break

    return continuous_days


def award_points(user, points, reason, activity=None):
    """
    给用户发放积分并记录积分流水

    Args:
        user: 用户对象
        points: 积分数量（整数，正数为增加，负数为扣除）
        reason: 积分变动原因（字符串）
        activity: 可选，关联的活动对象

    Returns:
        PointRecord: 创建的积分记录对象
    """
    # 确保积分是整数，避免非数字传入
    try:
        points = int(points)
    except (ValueError, TypeError):
        raise ValueError("积分数量必须是整数")

    # 创建积分记录（假设PointRecord模型有对应字段）
    point_record = PointRecord.objects.create(
        user=user,
        points=points,
        reason=reason,
        activity=activity,
        create_time=timezone.now()
    )

    # 可选：如果User模型有积分总数字段，同步更新
    # if hasattr(user, 'total_points'):
    #     user.total_points += points
    #     user.save(update_fields=['total_points'])

    return point_record