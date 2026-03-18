import pytest
from django.test import TestCase
from django.db.utils import IntegrityError
from apps.users.models import User
from apps.activities.models import Activity, ActivityMember
from apps.checkins.models import CheckIn, PointRecord


@pytest.mark.django_db
class TestModels(TestCase):
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create_user(
            username='teststudent',
            password='123456',
            student_id='224324',
            email='test@school.edu'
        )

        # 创建测试活动
        self.activity = Activity.objects.create(
            title='晨跑打卡',
            category='运动',
            creator=self.user,
            start_date='2026-03-01'
        )

    def test_user_add_points_and_level(self):
        """测试用户增加积分、总积分、等级与积分记录"""
        original_points = self.user.points
        original_total = self.user.total_points

        self.user.add_points(150)
        self.user.refresh_from_db()  # 确保从数据库重新加载

        self.assertEqual(self.user.points, original_points + 150)
        self.assertEqual(self.user.total_points, original_total + 150)
        self.assertEqual(self.user.level, 3)
        self.assertTrue(
            PointRecord.objects.filter(user=self.user, points=150).exists()
        )

    def test_checkin_unique_together_constraint(self):
        """测试：同一用户 + 同一活动 不可重复打卡（唯一约束）"""
        # 第一次打卡
        CheckIn.objects.create(
            user=self.user,
            activity=self.activity,
            content='今天跑了5公里！'
        )

        # 重复打卡应抛 IntegrityError
        with self.assertRaises(IntegrityError):
            CheckIn.objects.create(
                user=self.user,
                activity=self.activity,
                content='重复打卡'
            )

    def test_activity_member_creation_and_checkin_count(self):
        """测试活动成员创建与默认打卡次数"""
        member = ActivityMember.objects.create(
            activity=self.activity,
            user=self.user,
            role='member'
        )
        self.assertEqual(member.role, 'member')
        self.assertEqual(member.personal_checkins, 0)
        self.assertEqual(str(member), f'{self.user} - {self.activity}')