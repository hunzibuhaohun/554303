"""
活动视图 - 校园打卡平台
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, F
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Activity, Category, ActivityRegistration, ActivityComment
from .forms import ActivityForm, ActivityCommentForm


def activity_list(request):
    """活动列表视图"""
    activities = Activity.objects.filter(
        status__in=['upcoming', 'ongoing']
    ).select_related('category', 'creator').prefetch_related('participants')
    
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
    status = request.GET.get('status')
    if status:
        activities = activities.filter(status=status)
    
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
    }
    return render(request, 'activities/list.html', context)


def activity_detail(request, pk):
    """活动详情视图"""
    activity = get_object_or_404(
        Activity.objects.select_related('category', 'creator')
        .prefetch_related('participants', 'comments'),
        pk=pk
    )
    
    # 增加浏览次数
    activity.view_count += 1
    activity.save(update_fields=['view_count'])
    
    # 检查当前用户是否已报名
    is_registered = False
    can_checkin = False
    registration = None
    
    if request.user.is_authenticated:
        registration = ActivityRegistration.objects.filter(
            user=request.user,
            activity=activity
        ).first()
        is_registered = registration is not None
        
        # 检查是否可以打卡
        if is_registered:
            can_checkin = (registration.status == 'registered' and
                          activity.status == 'ongoing')
    
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
    }
    return render(request, 'activities/detail.html', context)


@login_required
def activity_create(request):
    """创建活动视图"""
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.creator = request.user
            activity.save()
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
    """编辑活动视图"""
    activity = get_object_or_404(Activity, pk=pk)
    
    # 检查权限
    if activity.creator != request.user and not request.user.is_staff:
        messages.error(request, '您没有权限编辑此活动。')
        return redirect('activities:detail', pk=pk)
    
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES, instance=activity)
        if form.is_valid():
            form.save()
            messages.success(request, '活动更新成功！')
            return redirect('activities:detail', pk=pk)
        else:
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
    """删除活动视图"""
    activity = get_object_or_404(Activity, pk=pk)
    
    # 检查权限
    if activity.creator != request.user and not request.user.is_staff:
        messages.error(request, '您没有权限删除此活动。')
        return redirect('activities:detail', pk=pk)
    
    if request.method == 'POST':
        activity.delete()
        messages.success(request, '活动已删除。')
        return redirect('activities:list')
    
    return render(request, 'activities/delete_confirm.html', {'activity': activity})


@login_required
@require_POST
def join_activity(request, pk):
    """报名参加活动（API）"""
    activity = get_object_or_404(Activity, pk=pk)
    
    # 检查是否可以报名
    if activity.is_full:
        return JsonResponse({'success': False, 'message': '活动已满员'})
    
    if activity.status != 'upcoming':
        return JsonResponse({'success': False, 'message': '活动不在报名阶段'})
    
    # 检查是否已报名
    if ActivityRegistration.objects.filter(user=request.user, activity=activity).exists():
        return JsonResponse({'success': False, 'message': '您已经报名了此活动'})
    
    # 创建报名记录
    registration = ActivityRegistration.objects.create(
        user=request.user,
        activity=activity
    )
    
    return JsonResponse({
        'success': True,
        'message': '报名成功',
        'points': activity.points
    })


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
        return JsonResponse({'success': False, 'message': '您未报名此活动'})
    
    if registration.status != 'registered':
        return JsonResponse({'success': False, 'message': '当前状态无法取消报名'})
    
    registration.delete()
    return JsonResponse({'success': True, 'message': '取消报名成功'})


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
        # 尝试多种方式查询
        try:
            # 方式1：通过 registrations 查询
            activities = Activity.objects.filter(
                registrations__user=request.user,
                registrations__status='approved'
            ).distinct()
        except:
            try:
                # 方式2：通过 activityregistration 查询
                activities = Activity.objects.filter(
                    activityregistration__user=request.user,
                    activityregistration__status='approved'
                ).distinct()
            except:
                # 方式3：通过用户反向查询
                reg_ids = request.user.activity_registrations.filter(
                    status='approved'
                ).values_list('activity_id', flat=True)
                activities = Activity.objects.filter(id__in=reg_ids)

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
# DRF ViewSet - 用于API路由（新增）
# ═══════════════════════════════════════════════════
from rest_framework import viewsets, permissions
from .serializers import ActivitySerializer, ActivityRegistrationSerializer


class ActivityViewSet(viewsets.ModelViewSet):
    """活动API视图集"""
    queryset = Activity.objects.filter(status='active')
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