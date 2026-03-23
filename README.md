# 仓库文件夹分析

## 顶层目录

- `apps/`：Django 业务应用集合，包含 users、activities、checkins、social、dashboard、api 等子应用。
- `campus_checkin/`：Django 项目级配置（URL、ASGI/WSGI、Celery、分环境 settings）。
- `templates/`：按业务模块拆分的 HTML 模板。
- `static/`：静态资源（CSS、JS、images）。
- `tests/`：自动化测试。
- `.git/`：Git 版本管理目录。

## apps/ 目录

- `apps/users/`：用户、积分、资料、关注关系等。
- `apps/activities/`：活动与分类、报名、评论等。
- `apps/checkins/`：打卡记录、打卡图片、打卡辅助工具。
- `apps/social/`：动态、点赞、评论、消息。
- `apps/dashboard/`：看板统计页面。
- `apps/api/`：REST API（序列化、视图、分页、路由）。
- 各应用下 `migrations/`：数据库迁移历史。

## 配置与路由层

- `campus_checkin/settings/`
  - `base.py`：基础配置、INSTALLED_APPS、中间件、数据库、静态媒体配置等。
  - `dev.py` / `prod.py`：开发与生产差异化配置。
- `campus_checkin/urls.py`：主路由，将请求分发到各业务应用。

## 前端资源层

- `templates/`：
  - `base.html` 公共骨架；
  - `users/`、`activities/`、`checkins/`、`social/`、`dashboard/` 对应各业务页面。
- `static/`：
  - `css/` 样式；
  - `js/` 前端脚本；
  - `images/` 图片资源目录。

## 测试与工程文件

- `tests/`：包含 API、打卡、模型相关测试。
- `requirements.txt`：依赖清单。
- `manage.py`：Django 管理入口。
- `start.sh` / `start.bat`：跨平台启动脚本。
- `PROJECT_STRUCTURE.md`：项目结构说明文档。

## 观察与结论

1. 目录结构是典型的 Django 多应用分层架构，业务边界清晰。
2. 文档中提到 `media/`、`logs/`、`scripts/`、`fixtures/` 等目录，但当前仓库未全部落地（可能在部署时创建）。
3. API 与页面模板双轨并存，支持服务端渲染与 REST 接口并行开发。
