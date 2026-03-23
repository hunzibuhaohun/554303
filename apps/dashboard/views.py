"""
数据看板视图 - 校园打卡平台
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta

from apps.users.models import User
from apps.activities.models import Activity, ActivityRegistration
from apps.checkins.models import CheckIn
from apps.social.models import Moment


@login_required
def statistics_view(request):
    """数据统计页面"""
    # 用户统计
    user_stats = {
        'total_users': User.objects.count(),
        'new_users_today': User.objects.filter(created_at__date=timezone.now().date()).count(),
        'new_users_week': User.objects.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
        'active_users': User.objects.filter(last_login__gte=timezone.now() - timedelta(days=7)).count(),
    }
    
    # 活动统计
    activity_stats = {
        'total_activities': Activity.objects.count(),
        'upcoming_activities': Activity.objects.filter(status='upcoming').count(),
        'ongoing_activities': Activity.objects.filter(status='ongoing').count(),
        'ended_activities': Activity.objects.filter(status='ended').count(),
        'total_participants': ActivityRegistration.objects.count(),
    }
    
    # 打卡统计
    checkin_stats = {
        'total_checkins': CheckIn.objects.filter(status='approved').count(),
        'checkins_today': CheckIn.objects.filter(
            status='approved',
            created_at__date=timezone.now().date()
        ).count(),
        'checkins_week': CheckIn.objects.filter(
            status='approved',
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count(),
        'total_points': User.objects.aggregate(total=Sum('points'))['total'] or 0,
    }
    
    # 社交统计
    social_stats = {
        'total_moments': Moment.objects.count(),
        'moments_week': Moment.objects.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
        'total_likes': Moment.objects.aggregate(total=Count('likes'))['total'] or 0,
    }
    
    # 积分排行榜
    top_users = User.objects.order_by('-points')[:10]
    
    # 热门活动
    hot_activities = Activity.objects.annotate(
        participant_count=Count('participants')
    ).order_by('-participant_count')[:5]
    
    context = {
        'user_stats': user_stats,
        'activity_stats': activity_stats,
        'checkin_stats': checkin_stats,
        'social_stats': social_stats,
        'top_users': top_users,
        'hot_activities': hot_activities,
    }
    
    return render(request, 'dashboard/statistics.html', context)


@login_required
def get_chart_data(request):
    """获取图表数据API"""
    chart_type = request.GET.get('type', 'checkin_trend')
    
    if chart_type == 'checkin_trend':
        # 近7天打卡趋势
        data = []
        labels = []
        for i in range(6, -1, -1):
            date = timezone.now().date() - timedelta(days=i)
            count = CheckIn.objects.filter(
                status='approved',
                created_at__date=date
            ).count()
            data.append(count)
            labels.append(date.strftime('%m-%d'))
        
        return JsonResponse({
            'labels': labels,
            'data': data,
            'title': '近7天打卡趋势'
        })
    
    elif chart_type == 'activity_category':
        # 活动分类统计
        categories = Activity.objects.values('category__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return JsonResponse({
            'labels': [c['category__name'] or '未分类' for c in categories],
            'data': [c['count'] for c in categories],
            'title': '活动分类分布'
        })
    
    elif chart_type == 'user_growth':
        # 用户增长趋势
        data = []
        labels = []
        for i in range(6, -1, -1):
            date = timezone.now().date() - timedelta(days=i)
            count = User.objects.filter(created_at__date__lte=date).count()
            data.append(count)
            labels.append(date.strftime('%m-%d'))
        
        return JsonResponse({
            'labels': labels,
            'data': data,
            'title': '用户增长趋势'
        })
    
    elif chart_type == 'points_distribution':
        # 积分分布
        ranges = [
            ('0-100', Q(points__gte=0, points__lt=100)),
            ('100-500', Q(points__gte=100, points__lt=500)),
            ('500-1000', Q(points__gte=500, points__lt=1000)),
            ('1000+', Q(points__gte=1000)),
        ]
        
        labels = []
        data = []
        for label, q in ranges:
            count = User.objects.filter(q).count()
            labels.append(label)
            data.append(count)
        
        return JsonResponse({
            'labels': labels,
            'data': data,
            'title': '用户积分分布'
        })
    
    return JsonResponse({'error': '未知的图表类型'})


@login_required
def personal_stats(request):
    """个人统计"""
    user = request.user
    
    # 打卡统计
    checkin_count = user.checkins.filter(status='approved').count()
    
    # 参与活动数
    joined_activities = ActivityRegistration.objects.filter(user=user).count()
    
    # 发布动态数
    moments_count = user.moments.count()
    
    # 获得点赞数
    likes_received = Moment.objects.filter(user=user).aggregate(
        total=Count('likes')
    )['total'] or 0
    
    # 近7天打卡数据
    checkin_data = []
    labels = []
    for i in range(6, -1, -1):
        date = timezone.now().date() - timedelta(days=i)
        count = user.checkins.filter(
            status='approved',
            created_at__date=date
        ).count()
        checkin_data.append(count)
        labels.append(date.strftime('%m-%d'))
    
    context = {
        'checkin_count': checkin_count,
        'joined_activities': joined_activities,
        'moments_count': moments_count,
        'likes_received': likes_received,
        'streak_days': user.streak_days,
        'checkin_labels': labels,
        'checkin_data': checkin_data,
    }
    
    return render(request, 'dashboard/personal_stats.html', context)
