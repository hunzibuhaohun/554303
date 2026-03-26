"""
活动视图 - 校园打卡平台
"""
import csv
from urllib.parse import urlencode
from datetime import timedelta
from apps.checkins.utils import calculate_continuous_days, award_points
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F, Count, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse,HttpResponse
from django.views.decorators.http import require_POST

from .models import Activity, Category, ActivityRegistration, ActivityComment
from .forms import ActivityForm, ActivityCommentForm
from apps.checkins.models import CheckIn
from apps.social.models import Moment,Message
from django.db import transaction

def activity_list(request):
    """活动列表视图"""

    # 先同步活动状态
    now = timezone.now()

    # 已结束
    Activity.objects.exclude(status='cancelled').filter(
        end_time__lt=now
    ).exclude(status='ended').update(status='ended')

    # 进行中
    Activity.objects.exclude(status='cancelled').filter(
        start_time__lte=now,
        end_time__gte=now
    ).exclude(status='ongoing').update(status='ongoing')

    # 即将开始
    Activity.objects.exclude(status='cancelled').filter(
        start_time__gt=now
    ).exclude(status='upcoming').update(status='upcoming')

    # 先取全部活动
    activities = Activity.objects.all().select_related(
        'category', 'creator'
    ).prefetch_related('participants')

    # 搜索
    q = request.GET.get('q')
    if q:
        activities = activities.filter(
            Q(title__icontains=q) | Q(location__icontains=q)
        )

    # 分类筛选
    category_id = request.GET.get('category')
    if category_id:
        activities = activities.filter(category_id=category_id)

    # 状态筛选
    status = request.GET.get('status', '')
    if status == 'all':
        pass
    elif status:
        activities = activities.filter(status=status)
    else:
        # 默认只显示即将开始和进行中的活动
        activities = activities.filter(status__in=['upcoming', 'ongoing'])

    # 仅显示可报名
    if request.GET.get('available_only'):
        activities = activities.filter(
            participants__lt=F('max_participants'),
            status='upcoming'
        )

    # 排序
    sort = request.GET.get('sort', '-created_at')
    activities = activities.order_by(sort)

    # 分页
    paginator = Paginator(activities, 9)
    page = request.GET.get('page')
    activities = paginator.get_page(page)

    # 保留查询参数
    query_params = ''
    if request.GET:
        params = request.GET.copy()
        if 'page' in params:
            del params['page']
        if params:
            query_params = '&' + params.urlencode()

    categories = Category.objects.all()

    context = {
        'activities': activities,
        'categories': categories,
        'query_params': query_params,
        'current_status': status,
        'current_category': category_id,
        'current_q': q,
    }
    return render(request, 'activities/list.html', context)

def activity_detail(request, pk):
    """活动详情视图"""
    activity = get_object_or_404(
        Activity.objects.select_related('category', 'creator')
        .prefetch_related('participants', 'comments', 'managers'),
        pk=pk
    )

    # 同步当前活动状态
    activity.update_status()
    activity.refresh_from_db()

    # 增加浏览次数
    activity.view_count += 1
    activity.save(update_fields=['view_count'])

    # 当前用户报名与权限
    is_registered = False
    can_checkin = False
    registration = None

    can_edit_activity = False
    can_delete_activity = False
    can_close_activity = False
    can_view_activity_dashboard = False

    if request.user.is_authenticated:
        registration = ActivityRegistration.objects.filter(
            user=request.user,
            activity=activity
        ).first()
        is_registered = registration is not None

        if is_registered:
            can_checkin = (
                registration.status == 'registered' and
                activity.status == 'ongoing'
            )

        can_edit_activity = activity.can_edit(request.user)
        can_delete_activity = activity.can_delete(request.user)
        can_close_activity = activity.can_close(request.user)

        # 创建者 / 活动管理者 / 总管理员 可看单活动数据面板
        can_view_activity_dashboard = can_edit_activity or can_close_activity

    # 相关活动推荐
    related_activities = Activity.objects.filter(
        category=activity.category,
        status__in=['upcoming', 'ongoing']
    ).exclude(id=activity.id)[:3]

    comment_form = ActivityCommentForm()

    # 单活动数据面板默认值
    activity_dashboard = None
    top_participants = []
    recent_participants = []
    recent_checkins = []
    pending_checkins = []
    rejected_checkins = []
    recent_moments = []
    recent_activity_comments = []

    # 关键：先给 management_data 默认值，避免普通用户访问时报错
    management_data = {
        'participant_page': None,
        'participant_keyword': '',
        'participant_status': '',
        'participant_querystring': '',

        'checkin_page': None,
        'checkin_keyword': '',
        'checkin_status': '',
        'checkin_querystring': '',

        'moment_page': None,
        'moment_keyword': '',
        'moment_querystring': '',

        'comment_page': None,
        'comment_keyword': '',
        'comment_querystring': '',
    }

    if can_view_activity_dashboard:
        registrations = ActivityRegistration.objects.filter(
            activity=activity
        ).select_related('user').order_by('-registered_at')

        active_registrations = registrations.exclude(status='cancelled')

        checkins = CheckIn.objects.filter(
            activity=activity
        ).select_related('user').order_by('-created_at')

        approved_checkins_qs = checkins.filter(status='approved')
        pending_checkins_qs = checkins.filter(status='pending')
        rejected_checkins_qs = checkins.filter(status='rejected')
        revoked_checkins_qs = checkins.filter(status='revoked')

        related_moments = Moment.objects.filter(
            activity=activity
        ).select_related('user').annotate(
            like_count=Count('likes', distinct=True)
        ).order_by('-created_at')

        total_registrations = active_registrations.count()
        registered_count = active_registrations.filter(status='registered').count()
        checked_in_count = active_registrations.filter(status='checked_in').count()
        completed_count = active_registrations.filter(status='completed').count()
        cancelled_count = registrations.filter(status='cancelled').count()

        approved_count = approved_checkins_qs.count()
        pending_count = pending_checkins_qs.count()
        rejected_count = rejected_checkins_qs.count()
        revoked_count = revoked_checkins_qs.count()

        total_points_sent = approved_checkins_qs.aggregate(
            total=Sum('points_earned')
        )['total'] or 0

        total_moments = related_moments.count()
        total_moment_likes = related_moments.aggregate(
            total=Count('likes', distinct=True)
        )['total'] or 0
        total_activity_comments = activity.comments.count()
        total_view_count = activity.view_count

        fill_rate = 0
        if activity.max_participants:
            fill_rate = round((total_registrations / activity.max_participants) * 100, 1)

        checkin_rate = 0
        if total_registrations:
            checkin_rate = round((approved_count / total_registrations) * 100, 1)

        completion_rate = 0
        if total_registrations:
            completion_rate = round((completed_count / total_registrations) * 100, 1)

        today = timezone.now().date()
        trend_labels = []
        registration_trend_data = []
        checkin_trend_data = []

        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            trend_labels.append(date.strftime('%m-%d'))
            registration_trend_data.append(
                registrations.filter(registered_at__date=date).count()
            )
            checkin_trend_data.append(
                approved_checkins_qs.filter(created_at__date=date).count()
            )

        activity_dashboard = {
            'total_registrations': total_registrations,
            'registered_count': registered_count,
            'checked_in_count': checked_in_count,
            'completed_count': completed_count,
            'cancelled_count': cancelled_count,
            'approved_checkins': approved_count,
            'pending_checkins': pending_count,
            'rejected_checkins': rejected_count,
            'revoked_checkins': revoked_count,
            'total_points_sent': total_points_sent,
            'moment_count': total_moments,
            'moment_like_count': total_moment_likes,
            'activity_comment_count': total_activity_comments,
            'view_count': total_view_count,
            'fill_rate': fill_rate,
            'checkin_rate': checkin_rate,
            'completion_rate': completion_rate,
            'registration_status_labels': ['待参与', '已打卡', '已完成', '已取消'],
            'registration_status_data': [
                registered_count,
                checked_in_count,
                completed_count,
                cancelled_count,
            ],
            'checkin_status_labels': ['通过', '待审核', '拒绝', '已撤销'],
            'checkin_status_data': [
                approved_count,
                pending_count,
                rejected_count,
                revoked_count,
            ],
            'trend_labels': trend_labels,
            'registration_trend_data': registration_trend_data,
            'checkin_trend_data': checkin_trend_data,
        }

        top_participants = active_registrations.order_by('-user__points', '-registered_at')[:10]
        recent_participants = registrations[:8]
        recent_checkins = approved_checkins_qs[:8]
        pending_checkins = pending_checkins_qs[:8]
        rejected_checkins = rejected_checkins_qs[:8]
        recent_moments = related_moments[:6]
        recent_activity_comments = activity.comments.select_related('user').order_by('-created_at')[:6]

        management_data = _build_activity_management_data(activity, request)

    context = {
        'activity': activity,
        'is_registered': is_registered,
        'can_checkin': can_checkin,
        'registration': registration,
        'related_activities': related_activities,
        'comments': activity.comments.filter(parent=None),
        'comment_form': comment_form,
        'can_edit_activity': can_edit_activity,
        'can_delete_activity': can_delete_activity,
        'can_close_activity': can_close_activity,
        'can_view_activity_dashboard': can_view_activity_dashboard,
        'activity_dashboard': activity_dashboard,
        'top_participants': top_participants,
        'recent_participants': recent_participants,
        'recent_checkins': recent_checkins,
        'pending_checkins': pending_checkins,
        'rejected_checkins': rejected_checkins,
        'recent_moments': recent_moments,
        'recent_activity_comments': recent_activity_comments,
        'management_data': management_data,
    }
    return render(request, 'activities/detail.html', context)

def _can_manage_activity(user, activity):
    """活动创建者 / 活动管理员 / 总管理员 可管理该活动"""
    if not user or not user.is_authenticated:
        return False
    return activity.can_edit(user) or activity.can_close(user)

def _filtered_get_params(querydict, exclude_keys=None):
    exclude_keys = exclude_keys or []
    data = querydict.copy()
    for key in exclude_keys:
        if key in data:
            del data[key]
    return data.urlencode()


def _build_activity_management_data(activity, request):
    # ===== 参与者 =====
    participant_keyword = request.GET.get('participant_q', '').strip()
    participant_status = request.GET.get('participant_status', '').strip()
    participant_page_number = request.GET.get('participant_page')

    participant_qs = ActivityRegistration.objects.filter(
        activity=activity
    ).select_related('user').order_by('-registered_at')

    if participant_keyword:
        participant_qs = participant_qs.filter(
            Q(user__username__icontains=participant_keyword) |
            Q(user__real_name__icontains=participant_keyword) |
            Q(user__department__icontains=participant_keyword)
        )

    if participant_status:
        participant_qs = participant_qs.filter(status=participant_status)

    participant_paginator = Paginator(participant_qs, 8)
    participant_page = participant_paginator.get_page(participant_page_number)

    # ===== 打卡 =====
    checkin_keyword = request.GET.get('checkin_q', '').strip()
    checkin_status = request.GET.get('checkin_status', '').strip()
    checkin_page_number = request.GET.get('checkin_page')

    checkin_qs = CheckIn.objects.filter(
        activity=activity
    ).select_related('user', 'reviewed_by').order_by('-created_at')

    if checkin_keyword:
        checkin_qs = checkin_qs.filter(
            Q(user__username__icontains=checkin_keyword) |
            Q(user__real_name__icontains=checkin_keyword) |
            Q(remark__icontains=checkin_keyword)
        )

    if checkin_status:
        checkin_qs = checkin_qs.filter(status=checkin_status)

    checkin_paginator = Paginator(checkin_qs, 8)
    checkin_page = checkin_paginator.get_page(checkin_page_number)

    # ===== 社交：动态 =====
    moment_keyword = request.GET.get('moment_q', '').strip()
    moment_page_number = request.GET.get('moment_page')

    moment_qs = Moment.objects.filter(
        activity=activity
    ).select_related('user').annotate(
        like_count=Count('likes', distinct=True)
    ).order_by('-created_at')

    if moment_keyword:
        moment_qs = moment_qs.filter(
            Q(user__username__icontains=moment_keyword) |
            Q(content__icontains=moment_keyword)
        )

    moment_paginator = Paginator(moment_qs, 6)
    moment_page = moment_paginator.get_page(moment_page_number)

    # ===== 社交：评论 =====
    comment_keyword = request.GET.get('comment_q', '').strip()
    comment_page_number = request.GET.get('comment_page')

    comment_qs = activity.comments.select_related('user').order_by('-created_at')

    if comment_keyword:
        comment_qs = comment_qs.filter(
            Q(user__username__icontains=comment_keyword) |
            Q(content__icontains=comment_keyword)
        )

    comment_paginator = Paginator(comment_qs, 6)
    comment_page = comment_paginator.get_page(comment_page_number)

    return {
        'participant_page': participant_page,
        'participant_keyword': participant_keyword,
        'participant_status': participant_status,
        'participant_querystring': _filtered_get_params(
            request.GET, ['participant_page']
        ),

        'checkin_page': checkin_page,
        'checkin_keyword': checkin_keyword,
        'checkin_status': checkin_status,
        'checkin_querystring': _filtered_get_params(
            request.GET, ['checkin_page']
        ),

        'moment_page': moment_page,
        'moment_keyword': moment_keyword,
        'moment_querystring': _filtered_get_params(
            request.GET, ['moment_page']
        ),

        'comment_page': comment_page,
        'comment_keyword': comment_keyword,
        'comment_querystring': _filtered_get_params(
            request.GET, ['comment_page']
        ),
    }


@login_required
@require_POST
def manage_registration_cancel(request, pk, registration_id):
    """活动管理员取消某个报名"""
    activity = get_object_or_404(Activity, pk=pk)

    if not _can_manage_activity(request.user, activity):
        messages.error(request, '您没有权限管理此活动。')
        return redirect('activities:detail', pk=pk)

    registration = get_object_or_404(
        ActivityRegistration,
        pk=registration_id,
        activity=activity
    )

    if registration.status == 'cancelled':
        messages.warning(request, '该报名已是取消状态。')
        return redirect('activities:detail', pk=pk)

    # 已完成的报名不再允许直接取消，避免数据混乱
    if registration.status == 'completed':
        messages.error(request, '已完成的报名不能直接取消。')
        return redirect('activities:detail', pk=pk)

    with transaction.atomic():
        registration.status = 'cancelled'
        registration.save(update_fields=['status'])

        # 如果存在待审核打卡，顺带驳回，避免报名取消后仍挂着待审核记录
        if hasattr(registration, 'checkin') and registration.checkin.status == 'pending':
            registration.checkin.reject(
                reviewer=request.user,
                note='报名已被活动管理员取消'
            )

    messages.success(request, f'已取消 {registration.user.username} 的报名。')
    return redirect('activities:detail', pk=pk)


@login_required
@require_POST
def manage_registration_complete(request, pk, registration_id):
    """活动管理员手动标记报名完成"""
    activity = get_object_or_404(Activity, pk=pk)

    if not _can_manage_activity(request.user, activity):
        messages.error(request, '您没有权限管理此活动。')
        return redirect('activities:detail', pk=pk)

    registration = get_object_or_404(
        ActivityRegistration,
        pk=registration_id,
        activity=activity
    )

    if registration.status == 'completed':
        messages.warning(request, '该报名已经是完成状态。')
        return redirect('activities:detail', pk=pk)

    if registration.status == 'cancelled':
        messages.error(request, '已取消的报名不能标记为完成。')
        return redirect('activities:detail', pk=pk)

    registration.status = 'completed'
    registration.save(update_fields=['status'])

    messages.success(request, f'已将 {registration.user.username} 标记为完成。')
    return redirect('activities:detail', pk=pk)


@login_required
@require_POST
def manage_checkin_approve(request, pk, checkin_id):
    """活动管理员审核通过打卡"""
    activity = get_object_or_404(Activity, pk=pk)

    if not _can_manage_activity(request.user, activity):
        messages.error(request, '您没有权限管理此活动。')
        return redirect('activities:detail', pk=pk)

    checkin = get_object_or_404(
        CheckIn,
        pk=checkin_id,
        activity=activity
    )

    if checkin.status != 'pending':
        messages.warning(request, '该打卡不是待审核状态，无法重复处理。')
        return redirect('activities:detail', pk=pk)

    review_note = request.POST.get('note', '').strip() or '活动管理员审核通过'

    with transaction.atomic():
        checkin.status = 'approved'
        checkin.reviewed_by = request.user
        checkin.review_note = review_note
        checkin.save(update_fields=['status', 'reviewed_by', 'review_note'])

        streak = calculate_continuous_days(checkin.user, checkin.activity)
        points = award_points(
            checkin.user,
            activity=activity,
            streak_days=streak,
            related_checkin=checkin
        )

        checkin.points_earned = points
        checkin.save(update_fields=['points_earned'])

        checkin.registration.status = 'completed'
        checkin.registration.save(update_fields=['status'])

        Message.objects.create(
            recipient=checkin.user,
            sender=request.user,
            message_type='activity',
            title='打卡审核已通过',
            content=(
                f'你在活动《{activity.title}》中的打卡已审核通过，'
                f'获得 {points} 积分。备注：{review_note}'
            ),
            related_activity=activity
        )

    messages.success(request, f'已通过 {checkin.user.username} 的打卡申请。')
    return redirect('activities:detail', pk=pk)


@login_required
@require_POST
def manage_checkin_reject(request, pk, checkin_id):
    """活动管理员驳回打卡"""
    activity = get_object_or_404(Activity, pk=pk)

    if not _can_manage_activity(request.user, activity):
        messages.error(request, '您没有权限管理此活动。')
        return redirect('activities:detail', pk=pk)

    checkin = get_object_or_404(
        CheckIn,
        pk=checkin_id,
        activity=activity
    )

    if checkin.status != 'pending':
        messages.warning(request, '该打卡不是待审核状态，无法重复处理。')
        return redirect('activities:detail', pk=pk)

    review_note = request.POST.get('note', '').strip() or '活动管理员审核拒绝'

    checkin.status = 'rejected'
    checkin.reviewed_by = request.user
    checkin.review_note = review_note
    checkin.save(update_fields=['status', 'reviewed_by', 'review_note'])

    checkin.registration.status = 'registered'
    checkin.registration.save(update_fields=['status'])

    Message.objects.create(
        recipient=checkin.user,
        sender=request.user,
        message_type='activity',
        title='打卡审核未通过',
        content=(
            f'你在活动《{activity.title}》中的打卡未通过审核。'
            f'原因：{review_note}'
        ),
        related_activity=activity
    )

    messages.success(request, f'已拒绝 {checkin.user.username} 的打卡申请。')
    return redirect('activities:detail', pk=pk)

@login_required
@require_POST
def manage_checkin_revoke(request, pk, checkin_id):
    """活动管理员撤销已通过打卡，并回收积分"""
    activity = get_object_or_404(Activity, pk=pk)

    if not _can_manage_activity(request.user, activity):
        messages.error(request, '您没有权限管理此活动。')
        return redirect('activities:detail', pk=pk)

    checkin = get_object_or_404(
        CheckIn.objects.select_related('user', 'registration', 'activity'),
        pk=checkin_id,
        activity=activity
    )

    if checkin.status != 'approved':
        messages.warning(request, '只有已通过的打卡才能撤销。')
        return redirect('activities:detail', pk=pk)

    revoke_note = request.POST.get('note', '').strip() or '活动管理员撤销通过'

    with transaction.atomic():
        deducted_points = int(checkin.points_earned or 0)

        # 回收积分
        if deducted_points > 0:
            checkin.user.add_points(
                -deducted_points,
                description=f'撤销活动《{activity.title}》打卡积分：{revoke_note}'
            )

        # 打卡状态改成 revoked
        checkin.status = 'revoked'
        checkin.reviewed_by = request.user
        checkin.review_note = f'撤销通过：{revoke_note}'
        checkin.points_earned = 0
        checkin.save(update_fields=['status', 'reviewed_by', 'review_note', 'points_earned'])

        # 报名状态退回 registered，允许后续重新打卡/重新审核
        checkin.registration.status = 'registered'
        checkin.registration.save(update_fields=['status'])

        Message.objects.create(
            recipient=checkin.user,
            sender=request.user,
            message_type='activity',
            title='打卡通过已被撤销',
            content=(
                f'你在活动《{activity.title}》中的已通过打卡已被管理员撤销。'
                f'原因：{revoke_note}。'
                f'已回收积分：{deducted_points} 分。'
            ),
            related_activity=activity
        )

    messages.success(
        request,
        f'已撤销 {checkin.user.username} 的通过打卡，并回收 {deducted_points} 积分。'
    )
    return redirect('activities:detail', pk=pk)

@login_required
def export_activity_participants_csv(request, pk):
    activity = get_object_or_404(Activity, pk=pk)

    if not _can_manage_activity(request.user, activity):
        messages.error(request, '您没有权限导出此活动数据。')
        return redirect('activities:detail', pk=pk)

    participant_keyword = request.GET.get('participant_q', '').strip()
    participant_status = request.GET.get('participant_status', '').strip()

    qs = ActivityRegistration.objects.filter(activity=activity).select_related('user').order_by('-registered_at')

    if participant_keyword:
        qs = qs.filter(
            Q(user__username__icontains=participant_keyword) |
            Q(user__real_name__icontains=participant_keyword) |
            Q(user__department__icontains=participant_keyword)
        )

    if participant_status:
        qs = qs.filter(status=participant_status)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="activity_{activity.id}_participants.csv"'

    writer = csv.writer(response)
    writer.writerow(['用户名', '姓名', '院系', '状态', '报名时间'])

    for reg in qs:
        writer.writerow([
            reg.user.username,
            reg.user.real_name,
            reg.user.department,
            reg.get_status_display(),
            reg.registered_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response


@login_required
def export_activity_checkins_csv(request, pk):
    activity = get_object_or_404(Activity, pk=pk)

    if not _can_manage_activity(request.user, activity):
        messages.error(request, '您没有权限导出此活动数据。')
        return redirect('activities:detail', pk=pk)

    checkin_keyword = request.GET.get('checkin_q', '').strip()
    checkin_status = request.GET.get('checkin_status', '').strip()

    qs = CheckIn.objects.filter(activity=activity).select_related('user', 'reviewed_by').order_by('-created_at')

    if checkin_keyword:
        qs = qs.filter(
            Q(user__username__icontains=checkin_keyword) |
            Q(user__real_name__icontains=checkin_keyword) |
            Q(remark__icontains=checkin_keyword)
        )

    if checkin_status:
        qs = qs.filter(status=checkin_status)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="activity_{activity.id}_checkins.csv"'

    writer = csv.writer(response)
    writer.writerow(['用户名', '状态', '备注', '审核备注', '积分', '打卡时间'])

    for checkin in qs:
        writer.writerow([
            checkin.user.username,
            checkin.get_status_display(),
            checkin.remark,
            checkin.review_note,
            checkin.points_earned,
            checkin.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response


@login_required
def export_activity_moments_csv(request, pk):
    activity = get_object_or_404(Activity, pk=pk)

    if not _can_manage_activity(request.user, activity):
        messages.error(request, '您没有权限导出此活动数据。')
        return redirect('activities:detail', pk=pk)

    moment_keyword = request.GET.get('moment_q', '').strip()

    qs = Moment.objects.filter(activity=activity).select_related('user').annotate(
        like_count=Count('likes', distinct=True)
    ).order_by('-created_at')

    if moment_keyword:
        qs = qs.filter(
            Q(user__username__icontains=moment_keyword) |
            Q(content__icontains=moment_keyword)
        )

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="activity_{activity.id}_moments.csv"'

    writer = csv.writer(response)
    writer.writerow(['发布者', '内容', '点赞数', '发布时间'])

    for moment in qs:
        writer.writerow([
            moment.user.username,
            moment.content,
            moment.like_count,
            moment.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response

@login_required
def activity_create(request):
    """创建活动视图：所有登录用户都可创建"""
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.creator = request.user
            activity.save()
            form.save_m2m()  # 保存 managers 多对多关系（前提：模型和表单已添加 managers）
            messages.success(request, '活动创建成功！')
            return redirect('activities:detail', pk=activity.pk)
        else:
            messages.error(request, '创建失败，请检查填写信息。')
    else:
        form = ActivityForm()

    categories = Category.objects.all()
    return render(request, 'activities/create.html', {
        'form': form,
        'categories': categories
    })


@login_required
def activity_edit(request, pk):
    """编辑活动视图：创建者和活动管理者可编辑；总管理员不能编辑"""
    activity = get_object_or_404(Activity, pk=pk)

    if not activity.can_edit(request.user):
        messages.error(request, '您没有权限编辑此活动。')
        return redirect('activities:detail', pk=pk)

    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES, instance=activity)
        if form.is_valid():
            form.save()
            messages.success(request, '活动更新成功！')
            return redirect('activities:detail', pk=pk)
        else:
            print("===== form.errors.as_json =====")
            print(form.errors.as_json())
            print("===== form.non_field_errors =====")
            print(form.non_field_errors())
            messages.error(request, '更新失败，请检查填写信息。')
    else:
        form = ActivityForm(instance=activity)

    categories = Category.objects.all()
    return render(request, 'activities/edit.html', {
        'form': form,
        'categories': categories,
        'activity': activity
    })


@login_required
def activity_delete(request, pk):
    """删除活动视图：只有创建者可删除"""
    activity = get_object_or_404(Activity, pk=pk)

    if not activity.can_delete(request.user):
        messages.error(request, '只有活动创建者可以删除此活动。')
        return redirect('activities:detail', pk=pk)

    if request.method == 'POST':
        activity.delete()
        messages.success(request, '活动已删除。')
        return redirect('activities:list')

    return render(request, 'activities/delete_confirm.html', {'activity': activity})


@login_required
@require_POST
def close_activity(request, pk):
    """总管理员关闭活动：只能关闭，不能编辑"""
    activity = get_object_or_404(Activity, pk=pk)

    if not activity.can_close(request.user):
        messages.error(request, '只有总管理员可以关闭活动。')
        return redirect('activities:detail', pk=pk)

    activity.status = 'cancelled'
    activity.closed_by = request.user
    activity.closed_at = timezone.now()
    activity.save(update_fields=['status', 'closed_by', 'closed_at'])

    messages.success(request, '活动已被管理员关闭。')
    return redirect('activities:detail', pk=pk)



@login_required
@require_POST
def join_activity(request, pk):
    """报名参加活动"""
    activity = get_object_or_404(Activity, pk=pk)

    # 活动已满员
    if activity.is_full:
        messages.error(request, '活动已满员')
        return redirect('activities:detail', pk=pk)

    # 只有即将开始的活动才能报名
    if activity.status != 'upcoming':
        messages.error(request, '活动当前不在报名阶段')
        return redirect('activities:detail', pk=pk)

    # 防止重复报名
    if ActivityRegistration.objects.filter(user=request.user, activity=activity).exists():
        messages.warning(request, '您已经报名了此活动')
        return redirect('activities:detail', pk=pk)

    # 创建报名记录
    ActivityRegistration.objects.create(
        user=request.user,
        activity=activity
    )

    messages.success(request, f'报名成功！本活动可获得 {activity.points} 积分')
    return redirect('activities:detail', pk=pk)



@login_required
@require_POST
def cancel_registration(request, pk):
    """取消报名"""
    activity = get_object_or_404(Activity, pk=pk)

    registration = ActivityRegistration.objects.filter(
        user=request.user,
        activity=activity
    ).first()

    if not registration:
        messages.error(request, '您尚未报名此活动')
        return redirect('activities:detail', pk=pk)

    if registration.status != 'registered':
        messages.error(request, '当前状态无法取消报名')
        return redirect('activities:detail', pk=pk)

    registration.delete()
    messages.success(request, '取消报名成功')
    return redirect('activities:detail', pk=pk)


@login_required
@require_POST
def add_comment(request, pk):
    """添加评论"""
    activity = get_object_or_404(Activity, pk=pk)
    form = ActivityCommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.activity = activity
        comment.user = request.user
        comment.save()
        messages.success(request, '评论发表成功！')
    else:
        messages.error(request, '评论发表失败。')

    return redirect('activities:detail', pk=pk)


@login_required
def my_activities(request):
    """我的活动"""
    activity_type = request.GET.get('type', 'created')

    if activity_type == 'created':
        activities = Activity.objects.filter(creator=request.user)

    elif activity_type == 'joined':
        # 报名成功 / 已打卡 / 已完成都算“我参加的活动”
        activities = Activity.objects.filter(
            participants__user=request.user,
            participants__status__in=['registered', 'checked_in', 'completed']
        ).distinct()

    elif activity_type == 'checked':
        from apps.checkins.models import CheckIn
        activity_ids = CheckIn.objects.filter(user=request.user).values_list('activity_id', flat=True)
        activities = Activity.objects.filter(id__in=activity_ids)

    else:
        activities = Activity.objects.filter(creator=request.user)

    return render(request, 'activities/my_activities.html', {
        'activities': activities,
        'current_type': activity_type,
        'user': request.user
    })


# ═══════════════════════════════════════════════════
# DRF ViewSet - 用于API路由
# ═══════════════════════════════════════════════════
from rest_framework import viewsets, permissions
from .serializers import ActivitySerializer, ActivityRegistrationSerializer


class ActivityViewSet(viewsets.ModelViewSet):
    """活动API视图集"""
    queryset = Activity.objects.filter(status__in=['upcoming', 'ongoing'])
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """创建时自动设置创建者"""
        serializer.save(creator=self.request.user)


class ActivityRegistrationViewSet(viewsets.ModelViewSet):
    """活动报名API视图集"""
    queryset = ActivityRegistration.objects.all()
    serializer_class = ActivityRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """只返回当前用户的报名记录"""
        return ActivityRegistration.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """创建时自动设置用户"""
        serializer.save(user=self.request.user)