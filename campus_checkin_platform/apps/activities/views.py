"""
活动视图 - 校园打卡平台
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Activity, Category, ActivityRegistration, ActivityComment
from .forms import ActivityForm, ActivityCommentForm


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
        .prefetch_related('participants', 'comments'),
        pk=pk
    )

    # 同步当前活动状态
    activity.update_status()
    activity.refresh_from_db()

    # 增加浏览次数
    activity.view_count += 1
    activity.save(update_fields=['view_count'])

    # 检查当前用户是否已报名
    is_registered = False
    can_checkin = False
    registration = None

    # 新增：权限变量，供模板使用
    can_edit_activity = False
    can_delete_activity = False
    can_close_activity = False

    if request.user.is_authenticated:
        registration = ActivityRegistration.objects.filter(
            user=request.user,
            activity=activity
        ).first()
        is_registered = registration is not None

        # 检查是否可以打卡
        if is_registered:
            can_checkin = (
                registration.status == 'registered' and
                activity.status == 'ongoing'
            )

        # 新增：活动权限判断
        can_edit_activity = activity.can_edit(request.user)
        can_delete_activity = activity.can_delete(request.user)
        can_close_activity = activity.can_close(request.user)

    # 相关活动推荐
    related_activities = Activity.objects.filter(
        category=activity.category,
        status__in=['upcoming', 'ongoing']
    ).exclude(id=activity.id)[:3]

    # 评论表单
    comment_form = ActivityCommentForm()

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
    }
    return render(request, 'activities/detail.html', context)


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