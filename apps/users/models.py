
"""
用户模型 - 校园打卡平台
说明：
- 为了尽量减少项目结构变动，内部角色值继续沿用 student / teacher / admin，
  但界面语义统一为 学生 / 活动管理员 / 平台管理员。
"""
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    GENDER_CHOICES = [
        ('male', '男'),
        ('female', '女'),
        ('secret', '保密'),
    ]

    ROLE_CHOICES = [
        ('student', '学生'),
        ('teacher', '活动管理员'),
        ('admin', '平台管理员'),
    ]

    student_id = models.CharField('学号', max_length=20, unique=True, null=True, blank=True)
    real_name = models.CharField('真实姓名', max_length=50, default='')
    gender = models.CharField('性别', max_length=10, choices=GENDER_CHOICES, default='secret')
    phone = models.CharField(
        '手机号',
        max_length=11,
        validators=[RegexValidator(r'^1[3-9]\d{9}$', '请输入有效的手机号')],
        blank=True,
    )

    department = models.CharField('院系', max_length=100, blank=True)
    major = models.CharField('专业', max_length=100, blank=True)
    grade = models.CharField('年级', max_length=20, blank=True)

    role = models.CharField('角色', max_length=20, choices=ROLE_CHOICES, default='student')
    is_verified = models.BooleanField('是否认证', default=False)

    avatar = models.ImageField(
        '头像',
        upload_to='avatars/%Y/%m/',
        default='avatars/default.png',
        blank=True,
    )
    bio = models.TextField('个人简介', max_length=500, blank=True)

    points = models.PositiveIntegerField('当前积分', default=0)
    total_checkins = models.PositiveIntegerField('累计打卡次数', default=0)

    streak_days = models.PositiveIntegerField('当前连续打卡天数', default=0)
    longest_streak = models.PositiveIntegerField('最长连续打卡天数', default=0)
    last_checkin_date = models.DateField('最后打卡日期', null=True, blank=True)

    activities_joined = models.PositiveIntegerField('参与活动数', default=0)
    activities_created = models.PositiveIntegerField('创建活动数', default=0)

    level = models.PositiveIntegerField('当前等级', default=1)
    level_title = models.CharField('等级称号', max_length=20, default='新手')

    followers = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='following',
        through='FollowRelation',
        blank=True,
    )

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    notify_activity = models.BooleanField('活动提醒', default=True)
    notify_checkin = models.BooleanField('打卡提醒', default=True)
    notify_system = models.BooleanField('系统公告', default=True)
    public_profile = models.BooleanField('公开个人资料', default=True)
    show_checkin = models.BooleanField('显示打卡记录', default=True)

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['department']),
            models.Index(fields=['points']),
            models.Index(fields=['streak_days']),
        ]

    def __str__(self):
        return f'{self.username} ({self.real_name or "未实名"})'

    def get_full_name(self):
        return self.real_name or self.username

    def get_short_name(self):
        return self.username

    def is_student(self):
        return self.role == 'student'

    def is_activity_manager(self):
        return self.role == 'teacher'

    def is_platform_admin(self):
        return self.role == 'admin'

    def can_create_activity(self):
        """
        活动创建统一走“活动申请 -> 平台管理员审核 -> 自动创建活动”流程。
        因此任何普通业务角色都不直接开放全局“创建活动”权限。
        """
        return False

    def can_manage_activity(self, activity):
        if not self.is_authenticated:
            return False
        if self.role == 'admin':
            return False
        if activity.creator_id == self.id:
            return True
        return activity.managers.filter(id=self.id).exists()

    def grant_activity_manager(self):
        """
        兼容旧代码保留的方法。
        现行规则下，活动审核通过后只授予“该活动”的管理权，不再提升为全局活动管理员。
        """
        return None

    @property
    def followers_count(self):
        return self.followers.count()

    @property
    def following_count(self):
        return self.following.count()

    @property
    def streak_days_calc(self):
        if not hasattr(self, '_streak_cache'):
            from apps.checkins.models import CheckIn

            checkins = CheckIn.objects.filter(user=self, status='approved').order_by('-created_at')
            if not checkins.exists():
                self._streak_cache = 0
                return 0

            streak = 0
            cursor = timezone.localdate()
            check_dates = set(c.check_in_date for c in checkins)

            if cursor not in check_dates:
                cursor -= timedelta(days=1)

            while cursor in check_dates:
                streak += 1
                cursor -= timedelta(days=1)

            self._streak_cache = streak

        return self._streak_cache

    def update_streak(self):
        from apps.checkins.models import CheckIn

        today = timezone.localdate()
        approved_dates = list(
            CheckIn.objects.filter(user=self, status='approved')
            .values_list('check_in_date', flat=True)
            .distinct()
            .order_by('-check_in_date')
        )
        if not approved_dates:
            self.streak_days = 0
            self.last_checkin_date = None
            self.save(update_fields=['streak_days', 'last_checkin_date'])
            return

        latest = approved_dates[0]
        if latest != today and (today - latest).days > 1:
            self.streak_days = 0
            self.last_checkin_date = latest
            self.save(update_fields=['streak_days', 'last_checkin_date'])
            return

        streak = 0
        cursor = latest
        date_set = set(approved_dates)
        while cursor in date_set:
            streak += 1
            cursor -= timedelta(days=1)

        self.streak_days = streak
        self.last_checkin_date = latest
        if streak > self.longest_streak:
            self.longest_streak = streak
        self.save(update_fields=['streak_days', 'last_checkin_date', 'longest_streak'])

    def check_streak_break(self):
        if not self.last_checkin_date:
            return
        today = timezone.localdate()
        if (today - self.last_checkin_date).days > 1 and self.streak_days != 0:
            self.streak_days = 0
            self.save(update_fields=['streak_days'])

    def add_points(self, points, description=''):
        points = int(points)
        self.points = max(0, self.points + points)
        self.save(update_fields=['points'])

        PointHistory.objects.create(
            user=self,
            amount=points,
            transaction_type='earn' if points >= 0 else 'deduct',
            description=description or '积分变动',
        )

        self.check_level_up()
        try:
            from apps.checkins.models import PointRecord
            PointRecord.objects.create(
                user=self,
                points=points,
                reason=description or '积分变动',
            )
        except Exception:
            pass

    def check_level_up(self):
        new_level = self.calculate_level()
        if new_level != self.level:
            self.level = new_level
            self.level_title = self.get_level_title(new_level)
            self.save(update_fields=['level', 'level_title'])

    def calculate_level(self):
        points = self.points
        if points < 100:
            return 1
        if points < 300:
            return 2
        if points < 600:
            return 3
        if points < 1000:
            return 4
        if points < 1500:
            return 5
        if points < 2200:
            return 6
        if points < 3000:
            return 7
        if points < 4000:
            return 8
        if points < 5500:
            return 9
        return 10

    @staticmethod
    def get_level_title(level):
        titles = {
            1: '新手',
            2: '活跃者',
            3: '打卡达人',
            4: '校园明星',
            5: '活动专家',
            6: '社交达人',
            7: '资深玩家',
            8: '传奇人物',
            9: '校园传说',
            10: '打卡之神',
        }
        return titles.get(level, '未知')

    @staticmethod
    def get_level_threshold(level):
        thresholds = {
            1: 0,
            2: 100,
            3: 300,
            4: 600,
            5: 1000,
            6: 1500,
            7: 2200,
            8: 3000,
            9: 4000,
            10: 5500,
        }
        return thresholds.get(level, 0)

    def get_next_level_points(self):
        thresholds = {
            1: 100,
            2: 300,
            3: 600,
            4: 1000,
            5: 1500,
            6: 2200,
            7: 3000,
            8: 4000,
            9: 5500,
            10: 999999,
        }
        return thresholds.get(self.level, 999999)

    def get_level_progress(self):
        current_threshold = self.get_level_threshold(self.level)
        next_threshold = self.get_next_level_points()
        if next_threshold == 999999:
            return 100
        progress = ((self.points - current_threshold) / (next_threshold - current_threshold)) * 100
        return min(100, max(0, progress))

    def increment_checkin_count(self):
        self.total_checkins += 1
        self.save(update_fields=['total_checkins'])

    @property
    def total_points(self):
        return self.points

    @property
    def continuous_days(self):
        return self.streak_days

    def increment_activity_joined(self):
        self.activities_joined += 1
        self.save(update_fields=['activities_joined'])

    def decrement_activity_joined(self):
        if self.activities_joined > 0:
            self.activities_joined -= 1
            self.save(update_fields=['activities_joined'])

    def increment_activity_created(self):
        self.activities_created += 1
        self.save(update_fields=['activities_created'])

    def decrement_activity_created(self):
        if self.activities_created > 0:
            self.activities_created -= 1
            self.save(update_fields=['activities_created'])

    def get_achievement_count(self):
        return self.achievements.count()

    def has_achievement(self, achievement_type):
        return self.achievements.filter(achievement_type=achievement_type).exists()

    def award_achievement(self, achievement_type, name, description, level='bronze'):
        achievement, created = UserAchievement.objects.get_or_create(
            user=self,
            achievement_type=achievement_type,
            defaults={
                'name': name,
                'description': description,
                'level': level,
            },
        )
        return created


class FollowRelation(models.Model):
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follow_relations_as_follower',
        verbose_name='关注者',
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follow_relations_as_following',
        verbose_name='被关注者',
    )
    created_at = models.DateTimeField('关注时间', auto_now_add=True)

    class Meta:
        unique_together = ['follower', 'following']
        verbose_name = '关注关系'
        verbose_name_plural = '关注关系'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.follower.username} 关注 {self.following.username}'


class UserAchievement(models.Model):
    ACHIEVEMENT_TYPES = [
        ('first_checkin', '首次打卡'),
        ('streak_3', '连续3天'),
        ('streak_7', '连续7天'),
        ('streak_30', '连续30天'),
        ('streak_100', '连续100天'),
        ('points_100', '积分破百'),
        ('points_500', '积分破五百'),
        ('points_1000', '积分破千'),
        ('creator', '活动创建者'),
        ('popular', '人气王'),
        ('social', '社交达人'),
    ]

    LEVEL_CHOICES = [
        ('bronze', '铜'),
        ('silver', '银'),
        ('gold', '金'),
        ('platinum', '白金'),
        ('diamond', '钻石'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements', verbose_name='用户')
    achievement_type = models.CharField('成就类型', max_length=20, choices=ACHIEVEMENT_TYPES)
    name = models.CharField('成就名称', max_length=50)
    description = models.TextField('成就描述', blank=True)
    icon = models.CharField('图标', max_length=50, default='🏅')
    level = models.CharField('等级', max_length=10, choices=LEVEL_CHOICES, default='bronze')
    earned_at = models.DateTimeField('获得时间', auto_now_add=True)

    class Meta:
        verbose_name = '用户成就'
        verbose_name_plural = '用户成就'
        unique_together = ['user', 'achievement_type']
        ordering = ['-earned_at']

    def __str__(self):
        return f'{self.user.username} - {self.name}'


class PointHistory(models.Model):
    TRANSACTION_TYPES = [
        ('earn', '获得'),
        ('spend', '消费'),
        ('deduct', '扣除'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_history', verbose_name='用户')
    amount = models.IntegerField('积分变动')
    transaction_type = models.CharField('交易类型', max_length=10, choices=TRANSACTION_TYPES, default='earn')
    description = models.CharField('描述', max_length=200)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '积分记录'
        verbose_name_plural = '积分记录'
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f'{self.user.username}: {sign}{self.amount} ({self.description})'


class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings_detail', verbose_name='用户')
    email_notification = models.BooleanField('邮件通知', default=True)
    push_notification = models.BooleanField('推送通知', default=True)
    show_email = models.BooleanField('公开邮箱', default=False)
    show_phone = models.BooleanField('公开手机', default=False)
    dark_mode = models.BooleanField('深色模式', default=False)
    language = models.CharField('语言', max_length=10, default='zh-CN')
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '用户设置'
        verbose_name_plural = '用户设置'

    def __str__(self):
        return f'{self.user.username} 的设置'
