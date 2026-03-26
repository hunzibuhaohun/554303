"""
数据看板视图 - 校园打卡平台
"""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.users.models import User
from apps.activities.models import Activity, ActivityRegistration
from apps.checkins.models import CheckIn
from apps.social.models import Moment


def _is_platform_admin(user):
    return getattr(user, 'role', '') == 'admin'


def _can_access_dashboard(user):
    return getattr(user, 'role', '') in ['teacher', 'admin']


def _get_visible_activities(user):
    """
    总管理员：全部活动
    活动管理员：自己创建的活动 + 被分配管理的活动
    """
    if _is_platform_admin(user):
        return Activity.objects.all()

    return Activity.objects.filter(
        Q(creator=user) | Q(managers=user)
    ).distinct()


@login_required
def statistics_view(request):
    """数据统计页面"""
    user = request.user

    if not _can_access_dashboard(user):
        messages.warning(request, '你暂无权限访问数据中心。')
        return redirect('index')

    now = timezone.now()
    today = now.date()
    visible_activities = _get_visible_activities(user)

    if _is_platform_admin(user):
        summary_cards = [
            {
                'title': '总用户数',
                'value': User.objects.count(),
                'subtitle': f"今日新增: {User.objects.filter(created_at__date=today).count()}",
                'icon': 'fa-users',
                'color': 'primary',
                'dark_text': False,
            },
            {
                'title': '总活动数',
                'value': Activity.objects.count(),
                'subtitle': f"进行中: {Activity.objects.filter(status='ongoing').count()}",
                'icon': 'fa-calendar-alt',
                'color': 'success',
                'dark_text': False,
            },
            {
                'title': '总打卡数',
                'value': CheckIn.objects.filter(status='approved').count(),
                'subtitle': f"今日: {CheckIn.objects.filter(status='approved', created_at__date=today).count()}",
                'icon': 'fa-check-circle',
                'color': 'info',
                'dark_text': False,
            },
            {
                'title': '总积分',
                'value': User.objects.aggregate(total=Sum('points'))['total'] or 0,
                'subtitle': '累计发放',
                'icon': 'fa-coins',
                'color': 'warning',
                'dark_text': True,
            },
        ]

        ranking_users = User.objects.order_by('-points', 'username')[:10]
        ranking_title = '积分排行榜'
        activity_list_title = '热门活动'
        page_title = '平台数据中心'
        page_subtitle = '查看全平台的用户、活动、打卡与积分统计'
        scope_badge = '总管理员视图'
        scope_badge_class = 'bg-danger-subtle text-danger'

        chart_config = [
            {'id': 'checkinChart', 'type': 'checkin_trend', 'title': '近7天打卡趋势'},
            {'id': 'categoryChart', 'type': 'activity_category', 'title': '活动分类分布'},
            {'id': 'userGrowthChart', 'type': 'user_growth', 'title': '近7天用户增长'},
            {'id': 'pointsChart', 'type': 'points_distribution', 'title': '用户积分分布'},
        ]
    else:
        registrations = ActivityRegistration.objects.filter(activity__in=visible_activities)
        approved_checkins = CheckIn.objects.filter(
            activity__in=visible_activities,
            status='approved',
        )
        related_moments = Moment.objects.filter(activity__in=visible_activities)

        summary_cards = [
            {
                'title': '我管理的活动数',
                'value': visible_activities.count(),
                'subtitle': f"即将开始: {visible_activities.filter(status='upcoming').count()}",
                'icon': 'fa-calendar-alt',
                'color': 'primary',
                'dark_text': False,
            },
            {
                'title': '进行中活动',
                'value': visible_activities.filter(status='ongoing').count(),
                'subtitle': f"已结束: {visible_activities.filter(status='ended').count()}",
                'icon': 'fa-bolt',
                'color': 'success',
                'dark_text': False,
            },
            {
                'title': '报名人次',
                'value': registrations.exclude(status='cancelled').count(),
                'subtitle': f"已完成: {registrations.filter(status='completed').count()}",
                'icon': 'fa-user-check',
                'color': 'info',
                'dark_text': False,
            },
            {
                'title': '发放积分',
                'value': approved_checkins.aggregate(total=Sum('points_earned'))['total'] or 0,
                'subtitle': f"关联动态: {related_moments.count()}",
                'icon': 'fa-coins',
                'color': 'warning',
                'dark_text': True,
            },
        ]

        ranking_users = User.objects.filter(
            activity_registrations__activity__in=visible_activities
        ).distinct().order_by('-points', 'username')[:10]

        ranking_title = '参与者积分排行'
        activity_list_title = '我管理的热门活动'
        page_title = '活动数据中心'
        page_subtitle = '仅展示你创建或被分配管理的活动数据'
        scope_badge = '活动管理员视图'
        scope_badge_class = 'bg-primary-subtle text-primary'

        chart_config = [
            {'id': 'checkinChart', 'type': 'checkin_trend', 'title': '近7天打卡趋势'},
            {'id': 'categoryChart', 'type': 'activity_category', 'title': '活动分类分布'},
        ]

    hot_activities = visible_activities.annotate(
        participant_count=Count('participants', distinct=True)
    ).order_by('-participant_count', '-created_at')[:5]

    context = {
        'page_title': page_title,
        'page_subtitle': page_subtitle,
        'scope_badge': scope_badge,
        'scope_badge_class': scope_badge_class,
        'summary_cards': summary_cards,
        'chart_config': chart_config,
        'ranking_users': ranking_users,
        'ranking_title': ranking_title,
        'activity_list_title': activity_list_title,
        'hot_activities': hot_activities,
        'is_platform_admin': _is_platform_admin(user),
        'visible_activity_count': visible_activities.count(),
    }
    return render(request, 'dashboard/statistics.html', context)


@login_required
def get_chart_data(request):
    """获取图表数据 API"""
    user = request.user

    if not _can_access_dashboard(user):
        return JsonResponse({'error': '无权访问数据中心'}, status=403)

    chart_type = request.GET.get('type', 'checkin_trend')
    is_admin = _is_platform_admin(user)
    visible_activities = _get_visible_activities(user)

    today = timezone.now().date()

    if chart_type == 'checkin_trend':
        labels = []
        data = []

        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            qs = CheckIn.objects.filter(
                status='approved',
                created_at__date=date,
            )
            if not is_admin:
                qs = qs.filter(activity__in=visible_activities)

            labels.append(date.strftime('%m-%d'))
            data.append(qs.count())

        return JsonResponse({
            'labels': labels,
            'data': data,
            'title': '近7天打卡趋势',
        })

    if chart_type == 'activity_category':
        categories = visible_activities.values('category__name').annotate(
            count=Count('id')
        ).order_by('-count')

        return JsonResponse({
            'labels': [item['category__name'] or '未分类' for item in categories],
            'data': [item['count'] for item in categories],
            'title': '活动分类分布',
        })

    if chart_type == 'user_growth':
        if not is_admin:
            return JsonResponse({'error': '当前角色不支持该图表'}, status=403)

        labels = []
        data = []

        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            count = User.objects.filter(created_at__date__lte=date).count()
            labels.append(date.strftime('%m-%d'))
            data.append(count)

        return JsonResponse({
            'labels': labels,
            'data': data,
            'title': '近7天用户增长',
        })

    if chart_type == 'points_distribution':
        if not is_admin:
            return JsonResponse({'error': '当前角色不支持该图表'}, status=403)

        ranges = [
            ('0-100', Q(points__gte=0, points__lt=100)),
            ('100-500', Q(points__gte=100, points__lt=500)),
            ('500-1000', Q(points__gte=500, points__lt=1000)),
            ('1000+', Q(points__gte=1000)),
        ]

        labels = []
        data = []
        for label, q in ranges:
            labels.append(label)
            data.append(User.objects.filter(q).count())

        return JsonResponse({
            'labels': labels,
            'data': data,
            'title': '用户积分分布',
        })

    return JsonResponse({'error': '未知的图表类型'}, status=400)


@login_required
def personal_stats(request):
    """
    兼容旧路由：不再渲染缺失模板，直接跳到个人中心。
    """
    messages.info(request, '个人统计入口已合并到个人中心。')
    return redirect('users:profile')