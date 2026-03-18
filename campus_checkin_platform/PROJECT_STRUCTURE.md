# 校园打卡平台 - 项目结构说明

## 目录结构

```
campus_checkin_platform/
├── apps/                          # Django应用目录
│   ├── __init__.py
│   ├── users/                     # 用户模块
│   │   ├── __init__.py
│   │   ├── admin.py              # 后台管理配置
│   │   ├── apps.py               # 应用配置
│   │   ├── forms.py              # 表单定义
│   │   ├── models.py             # 数据模型
│   │   ├── urls.py               # URL路由
│   │   └── views.py              # 视图函数
│   ├── activities/                # 活动模块
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── checkins/                  # 打卡模块
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   ├── utils.py              # 工具函数（定位验证）
│   │   └── views.py
│   ├── social/                    # 社交模块
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── dashboard/                 # 数据看板模块
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── urls.py
│   │   └── views.py
│   └── api/                       # API接口模块
│       ├── __init__.py
│       ├── apps.py
│       ├── pagination.py          # 分页配置
│       ├── serializers.py         # 序列化器
│       ├── urls.py
│       └── views.py
│
├── campus_checkin/                # 项目配置目录
│   ├── __init__.py
│   ├── asgi.py                   # ASGI配置
│   ├── celery.py                 # Celery配置
│   ├── urls.py                   # 主路由配置
│   ├── wsgi.py                   # WSGI配置
│   └── settings/                  # 分环境配置
│       ├── __init__.py
│       ├── base.py               # 基础配置
│       ├── dev.py                # 开发环境
│       └── prod.py               # 生产环境
│
├── templates/                     # 模板文件
│   ├── base.html                 # 基础模板
│   ├── index.html                # 首页
│   ├── users/                     # 用户模块模板
│   │   ├── login.html
│   │   ├── register.html
│   │   └── profile.html
│   ├── activities/                # 活动模块模板
│   │   ├── list.html
│   │   ├── detail.html
│   │   └── create.html
│   ├── checkins/                  # 打卡模块模板
│   │   ├── checkin.html
│   │   └── history.html
│   ├── social/                    # 社交模块模板
│   │   └── moments.html
│   └── dashboard/                 # 数据看板模板
│       └── statistics.html
│
├── static/                        # 静态文件
│   ├── css/
│   │   └── custom.css            # 自定义样式
│   ├── js/
│   │   └── main.js               # 主JavaScript文件
│   └── images/                    # 图片资源
│
├── media/                         # 用户上传文件
│   ├── avatars/                   # 用户头像
│   ├── activities/                # 活动封面
│   ├── checkins/                  # 打卡照片
│   └── moments/                   # 动态图片
│
├── logs/                          # 日志目录
├── fixtures/                      # 数据fixtures
├── scripts/                       # 部署脚本
│
├── manage.py                      # Django管理脚本
├── requirements.txt               # Python依赖
├── .env.example                   # 环境变量示例
├── .gitignore                     # Git忽略文件
├── start.sh                       # Linux/Mac启动脚本
├── start.bat                      # Windows启动脚本
├── README.md                      # 项目说明
└── PROJECT_STRUCTURE.md           # 项目结构说明
```

## 核心文件说明

### 配置文件

| 文件 | 说明 |
|------|------|
| `campus_checkin/settings/base.py` | Django基础配置 |
| `campus_checkin/settings/dev.py` | 开发环境配置 |
| `campus_checkin/settings/prod.py` | 生产环境配置 |
| `.env.example` | 环境变量示例 |

### 模型文件

| 文件 | 说明 |
|------|------|
| `apps/users/models.py` | User, FollowRelation, UserAchievement |
| `apps/activities/models.py` | Category, Activity, ActivityRegistration, ActivityComment |
| `apps/checkins/models.py` | CheckIn, CheckInPhoto |
| `apps/social/models.py` | Moment, MomentImage, MomentComment, Message |

### 视图文件

| 文件 | 说明 |
|------|------|
| `apps/users/views.py` | 登录、注册、个人中心、关注功能 |
| `apps/activities/views.py` | 活动列表、详情、创建、报名 |
| `apps/checkins/views.py` | 打卡、历史记录、位置验证 |
| `apps/social/views.py` | 动态发布、点赞、评论 |
| `apps/dashboard/views.py` | 数据统计、图表API |

### URL路由

| 文件 | 说明 |
|------|------|
| `campus_checkin/urls.py` | 主路由配置 |
| `apps/users/urls.py` | 用户模块路由 (/users/) |
| `apps/activities/urls.py` | 活动模块路由 (/activities/) |
| `apps/checkins/urls.py` | 打卡模块路由 (/checkins/) |
| `apps/social/urls.py` | 社交模块路由 (/social/) |
| `apps/dashboard/urls.py` | 数据看板路由 (/dashboard/) |
| `apps/api/urls.py` | API路由 (/api/) |

### 模板文件

| 文件 | 说明 |
|------|------|
| `templates/base.html` | 基础模板（导航、页脚、全局样式） |
| `templates/index.html` | 首页（Hero区域、热门活动、排行榜） |
| `templates/users/*.html` | 用户相关页面 |
| `templates/activities/*.html` | 活动相关页面 |
| `templates/checkins/*.html` | 打卡相关页面 |
| `templates/social/*.html` | 社交相关页面 |
| `templates/dashboard/*.html` | 数据看板页面 |

## 数据库模型关系

```
User (用户)
├── created_activities -> Activity (创建的活动)
├── activity_registrations -> ActivityRegistration (报名记录)
├── checkins -> CheckIn (打卡记录)
├── moments -> Moment (发布的动态)
├── followers (粉丝)
├── following (关注)
└── achievements -> UserAchievement (成就)

Activity (活动)
├── category -> Category (分类)
├── creator -> User (创建者)
├── participants -> ActivityRegistration (报名者)
├── checkins -> CheckIn (打卡记录)
└── comments -> ActivityComment (评论)

CheckIn (打卡)
├── user -> User (用户)
├── activity -> Activity (活动)
├── registration -> ActivityRegistration (报名记录)
└── photos -> CheckInPhoto (照片)

Moment (动态)
├── user -> User (发布者)
├── activity -> Activity (关联活动)
├── images -> MomentImage (图片)
├── likes (点赞用户)
└── comments -> MomentComment (评论)
```

## 技术栈版本

- Python: 3.10+
- Django: 4.2.7
- Django REST Framework: 3.14.0
- Bootstrap: 5.3.0
- Font Awesome: 6.4.0
- Chart.js: 最新版

## 启动方式

### 方式一：使用启动脚本（推荐）

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
./start.sh
```

### 方式二：手动启动

```bash
# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 启动服务器
python manage.py runserver
```

## 访问地址

- 首页: http://127.0.0.1:8000/
- 管理后台: http://127.0.0.1:8000/admin/
- API文档: http://127.0.0.1:8000/api/

## 默认账号

- 超级用户: admin / admin123
