"""
活动模型 - 校园打卡平台
核心模型文件，对应论文第三章「系统设计」中的 Activity 表结构
包含活动分类、活动主体、报名记录、活动评论四个模型
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class Category(models.Model):
    """活动分类模型
    用于对兴趣活动进行分类管理（运动、学习、艺术等）
    对应论文中「兴趣活动管理模块」的分类功能
    """
    name = models.CharField('分类名称', max_length=50, unique=True)
    icon = models.CharField('图标类名', max_length=50, default='fas fa-tag')      # 前端 Font Awesome 图标
    color = models.CharField('颜色', max_length=20, default='#3B82F6')            # 前端卡片颜色
    description = models.TextField('描述', blank=True)
    sort_order = models.PositiveIntegerField('排序', default=0)                   # 分类显示顺序
    is_active = models.BooleanField('是否启用', default=True)                     # 可禁用分类
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '活动分类'
        verbose_name_plural = '活动分类'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name


class Activity(models.Model):
    """活动模型（核心模型）
    对应论文表2.3 + 4.2.2节兴趣活动模块
    实现了活动发布、时间管理、地点打卡、积分奖励等所有功能
    """
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('upcoming', '即将开始'),
        ('ongoing', '进行中'),
        ('ended', '已结束'),
        ('cancelled', '已取消'),
    ]

    # ==================== 基本信息 ====================
    title = models.CharField('活动标题', max_length=100)
    description = models.TextField('活动描述')

    cover_image = models.ImageField(
        '封面图片',
        upload_to='activities/covers/%Y/%m/',
        default='activities/default.jpg'
    )

    # ==================== 关联字段 ====================
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='分类'
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,                    # 使用 settings 中的用户模型（支持自定义User）
        on_delete=models.CASCADE,
        related_name='created_activities',
        verbose_name='创建者'
    )

    # ==================== 时间信息 ====================
    start_time = models.DateTimeField('开始时间')
    end_time = models.DateTimeField('结束时间')
    registration_deadline = models.DateTimeField('报名截止时间', null=True, blank=True)

    # ==================== 地点信息（支持地图打卡） ====================
    location = models.CharField('活动地点', max_length=200)
    location_lat = models.DecimalField('纬度', max_digits=10, decimal_places=7, null=True, blank=True)
    location_lng = models.DecimalField('经度', max_digits=10, decimal_places=7, null=True, blank=True)

    # ==================== 参与限制 ====================
    max_participants = models.PositiveIntegerField('最大参与人数', default=50)
    min_participants = models.PositiveIntegerField('最小参与人数', default=1)

    # ==================== 积分与激励（论文核心功能） ====================
    points = models.PositiveIntegerField('积分奖励', default=10)

    # ==================== 状态管理 ====================
    status = models.CharField(
        '状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='upcoming'
    )

    # ==================== 额外规则 ====================
    requirements = models.TextField('参与要求', blank=True)
    allow_checkin_before_start = models.BooleanField('允许开始前打卡', default=False)
    checkin_radius = models.PositiveIntegerField('打卡范围(米)', default=500)

    # ==================== 统计字段 ====================
    view_count = models.PositiveIntegerField('浏览次数', default=0)

    # ==================== 时间戳 ====================
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

    # ==================== 自定义属性（模板和前端直接使用） ====================
    @property
    def is_hot(self):
        """是否热门活动（报名人数接近上限）"""
        return self.participants.count() > self.max_participants * 0.8

    @property
    def registration_percentage(self):
        """报名进度百分比（进度条显示）"""
        if self.max_participants == 0:
            return 0
        return int(self.participants.count() / self.max_participants * 100)

    @property
    def is_full(self):
        """是否已满员"""
        return self.participants.count() >= self.max_participants

    def update_status(self):
        """自动更新活动状态（可被定时任务调用）"""
        now = timezone.now()
        if self.status == 'cancelled':
            return
        if now < self.start_time:
            self.status = 'upcoming'
        elif self.start_time <= now <= self.end_time:
            self.status = 'ongoing'
        else:
            self.status = 'ended'
        self.save(update_fields=['status'])


class ActivityRegistration(models.Model):
    """活动报名记录模型
    记录学生报名 + 打卡状态，对应论文中「活动成员关系」和「打卡记录」
    """
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
        verbose_name='用户'
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='participants',          # Activity.participants 可直接获取报名人数
        verbose_name='活动'
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='registered'
    )
    registered_at = models.DateTimeField('报名时间', auto_now_add=True)
    checked_in_at = models.DateTimeField('打卡时间', null=True, blank=True)

    class Meta:
        unique_together = ['user', 'activity']   # 防止同一用户重复报名同一活动
        verbose_name = '活动报名'
        verbose_name_plural = '活动报名'

    def __str__(self):
        """完整字符串表示"""
        return f"{self.user.username} - {self.activity.title} ({self.get_status_display()})"


class ActivityComment(models.Model):
    """活动评论模型（对应论文社交互动模块）
    支持学生在活动下发表评论、回复他人评论，实现平台社交互动功能
    """
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='所属活动'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_comments',
        verbose_name='评论用户'
    )
    content = models.TextField('评论内容')

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='父评论'
    )

    # 扩展实用字段（论文和前端都非常需要）
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
        username = self.user.username if hasattr(self.user, 'username') else str(self.user)
        return f"{username}: {self.content[:30]}..."

    @property
    def is_parent(self):
        """是否为一级评论（非回复）"""
        return self.parent is None

    @property
    def is_reply(self):
        """是否为回复评论"""
        return self.parent is not None