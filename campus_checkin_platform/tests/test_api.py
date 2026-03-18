import pytest
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from apps.users.models import User
from apps.activities.models import Activity
from apps.checkins.models import CheckIn


@pytest.mark.django_db
class TestCheckInAPI(APITestCase):
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testapi',
            password='123456',
            student_id='224324'
        )
        # 强制登录
        self.client.force_authenticate(user=self.user)

        # 创建测试活动
        self.activity = Activity.objects.create(
            title='测试活动',
            category='学习',
            creator=self.user
        )

    def test_user_register_api(self):
        """测试用户注册接口"""
        url = reverse('register')  # 与你 urls name 保持一致
        data = {
            'username': 'newstudent',
            'password': '123456',
            'student_id': '2024001',
            'email': 'new@school.edu'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_login_api(self):
        """测试用户登录接口"""
        url = reverse('login')
        data = {
            'username': 'testapi',
            'password': '123456'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_checkin_create_api(self):
        """测试打卡提交接口（核心业务）"""
        url = reverse('checkin-list')  # ViewSet 默认路由
        data = {
            'activity': self.activity.id,
            'content': '今天完成了打卡任务！',
            'image': None
        }
        response = self.client.post(url, data, format='json')

        # 断言返回状态
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 断言数据库真的生成了打卡记录
        self.assertEqual(CheckIn.objects.count(), 1)

        # 断言用户积分增加
        self.user.refresh_from_db()
        self.assertGreater(self.user.points, 0)

    def test_checkin_duplicate_forbidden(self):
        """测试重复打卡被接口拒绝"""
        url = reverse('checkin-list')
        data = {
            'activity': self.activity.id,
            'content': '第一次打卡'
        }
        # 第一次打卡
        self.client.post(url, data, format='json')

        # 第二次打卡（同一活动同一天）
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)