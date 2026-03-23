# 校园兴趣打卡平台

基于Python的校园兴趣活动管理系统，集活动发布、打卡签到、社交互动、积分激励于一体。

## 项目信息

- **题目**：基于Python的校园打卡平台的设计与实现
- **学生**：余俊毅（学号224324）
- **学校**：江西警察学院网络安全学院
- **专业**：信息安全
- **指导教师**：戴虹

## 技术栈

- **后端**：Python 3.10+ + Django 4.2
- **前端**：HTML5 + Bootstrap 5 + JavaScript
- **数据库**：MySQL 8.0 / SQLite（开发环境）
- **缓存**：Redis
- **任务队列**：Celery
- **API框架**：Django REST Framework

## 核心功能

### 1. 用户管理
- 用户注册/登录（支持学号登录）
- 个人资料管理
- 关注/粉丝系统
- 积分与成就系统

### 2. 活动管理
- 活动发布、编辑、删除
- 活动分类管理
- 活动报名系统
- 活动评论互动

### 3. 打卡系统
- GPS定位验证
- 现场拍照上传
- 打卡审核机制
- 积分奖励发放

### 4. 社交互动
- 动态发布（支持图片）
- 点赞、评论功能
- 消息通知系统

### 5. 数据看板
- 打卡趋势统计
- 积分排行榜
- 活动数据分析
- 可视化图表

## 项目结构

```
campus_checkin_platform/
├── apps/                    # 应用目录
│   ├── users/              # 用户模块
│   ├── activities/         # 活动模块
│   ├── checkins/           # 打卡模块
│   ├── social/             # 社交模块
│   ├── dashboard/          # 数据看板
│   └── api/                # API接口
├── campus_checkin/         # 项目配置
│   ├── settings/           # 分环境配置
│   ├── urls.py            # 主路由
│   └── wsgi.py            # WSGI配置
├── templates/              # 模板文件
├── static/                 # 静态文件
├── media/                  # 用户上传文件
├── requirements.txt        # 依赖列表
├── manage.py              # 管理脚本
├── start.sh               # Linux/Mac启动脚本
└── start.bat              # Windows启动脚本
```

## 快速开始

### 1. 环境准备

确保已安装：
- Python 3.10+
- MySQL 8.0（可选，开发环境可使用SQLite）
- Redis（可选）

### 2. 克隆项目

```bash
cd campus_checkin_platform
```

### 3. 配置环境变量

复制环境变量示例文件并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库等信息。

### 4. 运行启动脚本

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

### 5. 访问系统

- 首页：http://127.0.0.1:8000/
- 管理后台：http://127.0.0.1:8000/admin/ （admin / admin123）

## 手动部署

如果不想使用启动脚本，可以手动执行：

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 收集静态文件
python manage.py collectstatic --noinput

# 创建超级用户
python manage.py createsuperuser

# 启动服务器
python manage.py runserver
```

## API接口

系统提供RESTful API接口，使用JWT认证：

- `POST /api/token/` - 获取访问令牌
- `POST /api/token/refresh/` - 刷新令牌
- `GET /api/activities/` - 活动列表
- `POST /api/activities/{id}/join/` - 报名活动
- `GET /api/checkins/` - 打卡记录
- `GET /api/moments/` - 动态列表

## 开发说明

### 添加新的活动分类

登录管理后台，在"活动分类"中添加新的分类。

### 配置高德地图API

在 `.env` 文件中设置 `AMAP_KEY`，用于位置逆编码。

### 配置邮件发送

在 `.env` 文件中配置邮件服务器信息。

## 许可证

本项目为毕业设计项目，仅供学习参考。

## 致谢

感谢指导教师戴虹老师的悉心指导！
