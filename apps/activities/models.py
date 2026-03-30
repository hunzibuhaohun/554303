
"""
活动模型 - 校园打卡平台
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField('分类名称', max_length=50, unique=True)
    icon = models.CharField('图标类名', max_length=50, default='fas fa-tag')
    color = models.CharField('颜色', max_length=20, default='#3B82F6')
    description = models.TextField('描述', blank=True)
    sort_order = models.PositiveIntegerField('排序', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '活动分类'
        verbose_name_plural = '活动分类'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name


class Activity(models.Model):
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('upcoming', '即将开始'),
        ('ongoing', '进行中'),
        ('ended', '已结束'),
        ('cancelled', '已取消'),
    ]
    CHECKIN_REVIEW_MODE_CHOICES = [
        ('auto', '自动通过'),
        ('manual', '人工审核'),
        ('risk', '异常审核'),
    ]

    title = models.CharField('活动标题', max_length=100)
    description = models.TextField('活动描述')
    cover_image = models.ImageField('封面图片', upload_to='activities/covers/%Y/%m/', blank=True, null=True)

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, verbose_name='分类')
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_activities',
        verbose_name='创建者',
    )
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='managed_activities',
        blank=True,
        verbose_name='活动管理者',
    )

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_activities',
        verbose_name='关闭操作人',
    )
    closed_at = models.DateTimeField('关闭时间', null=True, blank=True)

    start_time = models.DateTimeField('开始时间')
    end_time = models.DateTimeField('结束时间')
    registration_deadline = models.DateTimeField('报名截止时间', null=True, blank=True)

    location = models.CharField('活动地点', max_length=200)
    location_lat = models.DecimalField('纬度', max_digits=10, decimal_places=7, null=True, blank=True)
    location_lng = models.DecimalField('经度', max_digits=10, decimal_places=7, null=True, blank=True)

    max_participants = models.PositiveIntegerField('最大参与人数', default=50)
    min_participants = models.PositiveIntegerField('最小参与人数', default=1)
    points = models.PositiveIntegerField('积分奖励', default=10)

    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='upcoming')

    requirements = models.TextField('参与要求', blank=True)
    allow_checkin_before_start = models.BooleanField('允许开始前打卡', default=False)
    checkin_radius = models.PositiveIntegerField('打卡范围(米)', default=500)
    checkin_review_mode = models.CharField(
        '打卡审核模式',
        max_length=10,
        choices=CHECKIN_REVIEW_MODE_CHOICES,
        default='auto',
    )

    view_count = models.PositiveIntegerField('浏览次数', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '活动'
        verbose_name_plural = '活动'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'start_time']),
            models.Index(fields=['category']),
            models.Index(fields=['creator']),
        ]

    def __str__(self):
        return self.title

    def get_active_registration_count(self):
        return self.participants.exclude(status='cancelled').count()

    def can_edit(self, user):
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'role', None) == 'admin':
            return False
        if self.creator_id == user.id:
            return True
        return self.managers.filter(id=user.id).exists()

    def can_delete(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.creator_id == user.id or getattr(user, 'role', None) == 'admin'

    def can_close(self, user):
        if not user or not user.is_authenticated:
            return False
        return getattr(user, 'role', None) == 'admin'

    @property
    def is_hot(self):
        if self.max_participants <= 0:
            return False
        return self.get_active_registration_count() >= self.max_participants * 0.8

    @property
    def registration_percentage(self):
        if self.max_participants == 0:
            return 0
        return int((self.get_active_registration_count() / self.max_participants) * 100)

    @property
    def is_full(self):
        return self.get_active_registration_count() >= self.max_participants

    def update_status(self):
        if self.status == 'cancelled':
            return
        now = timezone.now()
        if now < self.start_time:
            new_status = 'upcoming'
        elif self.start_time <= now <= self.end_time:
            new_status = 'ongoing'
        else:
            new_status = 'ended'

        if new_status != self.status:
            self.status = new_status
            self.save(update_fields=['status'])


class ActivityRegistration(models.Model):
    STATUS_CHOICES = [
        ('registered', '已报名'),
        ('checked_in', '已打卡'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_registrations',
        verbose_name='用户',
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name='活动',
    )
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='registered')
    registered_at = models.DateTimeField('报名时间', auto_now_add=True)
    checked_in_at = models.DateTimeField('打卡时间', null=True, blank=True)

    class Meta:
        unique_together = ['user', 'activity']
        verbose_name = '活动报名'
        verbose_name_plural = '活动报名'

    def __str__(self):
        return f'{self.user.username} - {self.activity.title} ({self.get_status_display()})'


class ActivityComment(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='comments', verbose_name='所属活动')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_comments',
        verbose_name='评论用户',
    )
    content = models.TextField('评论内容')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='父评论',
    )
    like_count = models.PositiveIntegerField('点赞数', default=0)
    is_active = models.BooleanField('是否显示', default=True)
    created_at = models.DateTimeField('评论时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '活动评论'
        verbose_name_plural = '活动评论'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['activity']),
            models.Index(fields=['user']),
            models.Index(fields=['parent']),
        ]

    def __str__(self):
        return f'{self.user.username}: {self.content[:30]}...'

    @property
    def is_parent(self):
        return self.parent is None

    @property
    def is_reply(self):
        return self.parent is not None


class ActivityApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已驳回'),
    ]

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_applications',
        verbose_name='申请人',
    )
    title = models.CharField('拟申请活动标题', max_length=100)
    description = models.TextField('活动说明')
    apply_reason = models.TextField('申请理由', blank=True)

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='分类')
    cover_image = models.ImageField('封面图片', upload_to='activities/applications/%Y/%m/', blank=True, null=True)

    start_time = models.DateTimeField('计划开始时间')
    end_time = models.DateTimeField('计划结束时间')
    registration_deadline = models.DateTimeField('计划报名截止时间', null=True, blank=True)

    location = models.CharField('计划地点', max_length=200)
    location_lat = models.DecimalField('纬度', max_digits=10, decimal_places=7, null=True, blank=True)
    location_lng = models.DecimalField('经度', max_digits=10, decimal_places=7, null=True, blank=True)

    max_participants = models.PositiveIntegerField('最大参与人数', default=50)
    min_participants = models.PositiveIntegerField('最小参与人数', default=1)
    points = models.PositiveIntegerField('积分奖励', default=10)
    requirements = models.TextField('参与要求', blank=True)
    checkin_radius = models.PositiveIntegerField('打卡范围(米)', default=500)
    checkin_review_mode = models.CharField(
        '打卡审核模式',
        max_length=10,
        choices=Activity.CHECKIN_REVIEW_MODE_CHOICES,
        default='auto',
    )

    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    review_note = models.TextField('审核意见', blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_activity_applications',
        verbose_name='审核人',
    )
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)
    created_activity = models.ForeignKey(
        Activity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_applications',
        verbose_name='生成的活动',
    )

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '活动申请'
        verbose_name_plural = '活动申请'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.applicant.username} - {self.title}'

    @property
    def can_be_reviewed(self):
        return self.status == 'pending'
