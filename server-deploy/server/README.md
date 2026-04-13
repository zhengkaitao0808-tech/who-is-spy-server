# 谁是卧底小程序 - Django 后端

## 项目概述

基于 Django + Django Channels 开发的"谁是卧底"多人在线游戏后端，部署于微信云托管。

## 技术栈

- **框架**: Django 4.x + Django REST Framework
- **实时通信**: Django Channels + WebSocket
- **数据库**: MySQL (微信云托管)
- **缓存**: Redis (微信云托管内置)
- **部署**: Docker (微信云托管)

## 项目结构

```
server/
├── apps/                    # Django 应用
│   ├── users/              # 用户模块
│   │   ├── models.py       # 用户模型
│   │   ├── views.py       # 用户视图
│   │   ├── serializers.py  # 序列化器
│   │   └── urls.py         # 路由
│   ├── rooms/              # 房间模块
│   │   ├── models.py       # 房间模型
│   │   ├── views.py       # 房间视图
│   │   ├── serializers.py  # 序列化器
│   │   └── urls.py         # 路由
│   └── games/              # 游戏模块
│       ├── models.py       # 游戏模型
│       ├── views.py        # 游戏视图
│       ├── consumers.py    # WebSocket 消费者
│       ├── serializers.py  # 序列化器
│       └── urls.py          # 路由
├── config/                  # 项目配置
│   ├── settings.py         # Django 设置
│   ├── urls.py             # 根路由
│   ├── wsgi.py             # WSGI 配置
│   ├── asgi.py             # ASGI 配置 (Channels)
│   └── channels.py         # Channels 路由
├── Dockerfile              # Docker 配置
├── requirements.txt        # Python 依赖
├── manage.py               # Django 管理脚本
└── README.md               # 部署文档
```

## API 列表

### 用户接口
- `POST /api/user/login/` - 微信登录
- `GET /api/user/profile/` - 获取用户信息
- `PUT /api/user/profile/` - 更新用户信息

### 房间接口
- `POST /api/room/create/` - 创建房间
- `POST /api/room/join/` - 加入房间
- `POST /api/room/leave/` - 离开房间
- `GET /api/room/list/` - 房间列表
- `GET /api/room/<room_code>/` - 获取房间详情
- `POST /api/room/<room_code>/ready/` - 准备/取消准备

### 游戏接口
- `POST /api/game/start/` - 开始游戏
- `GET /api/game/word/` - 获取词语
- `POST /api/game/speak/` - 发言
- `POST /api/game/vote/` - 投票
- `GET /api/game/result/` - 游戏结果
- `POST /api/game/next_round/` - 下一轮

### WebSocket 端点
- `ws://domain/ws/room/<room_code>/` - 房间实时通信

## 环境变量

微信云托管需要配置以下环境变量：

| 变量名 | 说明 | 示例值 |
|-------|------|--------|
| WECHAT_APPID | 微信小程序AppID | wx4b601ea7ebee9d0f |
| WECHAT_SECRET | 微信小程序AppSecret | 55db6ccd69ffa3683d595e30fc0f31d1 |
| DJANGO_SECRET_KEY | Django密钥 | 自定义随机字符串 |
| DEBUG | 调试模式 | false |
| DB_HOST | 数据库主机 | 云托管自动注入 |
| DB_PORT | 数据库端口 | 云托管自动注入 |
| DB_USER | 数据库用户名 | root |
| DB_PASSWORD | 数据库密码 | 2kG7YeJJ |
| DB_NAME | 数据库名称 | 云托管自动注入 |
| REDIS_HOST | Redis主机 | 云托管自动注入 |
| REDIS_PORT | Redis端口 | 云托管自动注入 |

## 本地开发

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置本地环境变量
export WECHAT_APPID=wx4b601ea7ebee9d0f
export WECHAT_SECRET=55db6ccd69ffa3683d595e30fc0f31d1
export DJANGO_SECRET_KEY=your-secret-key-here
export DEBUG=True
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=who_is_spy

# 4. 创建数据库（MySQL）
mysql -u root -p -e "CREATE DATABASE who_is_spy CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 5. 运行迁移
python manage.py makemigrations
python manage.py migrate

# 6. 加载词库数据
python manage.py loaddata database/words.json

# 7. 启动开发服务器
python manage.py runserver

# 8. 测试 WebSocket（开发环境）
# 需要安装 channels 并配置 InMemoryChannelLayer
```

## 微信云托管部署

### 方式一：通过微信开发者工具部署

1. 在微信开发者工具中打开项目
2. 打开「云开发」面板
3. 选择「云托管」
4. 点击「部署」按钮
5. 选择 server 目录进行部署

### 方式二：通过命令行部署

```bash
# 1. 安装微信云托管 CLI
npm install -g @cloudbase/cli

# 2. 登录
tcb login

# 3. 部署到云托管
cd server
tcb cloudbase deploy --env-id prod-4g78pk7d990ffba9
```

### Dockerfile 说明

项目提供了优化的 Dockerfile，支持：
- 多阶段构建减小镜像体积
- 自动安装 Python 依赖
- 运行 Django 迁移
- 加载词库数据
- 启动 ASGI 服务器（Daphne）

## API 调用示例

### 微信登录
```bash
curl -X POST https://django-9ej9-245877-5-1421749290.sh.run.tcloudbase.com/api/user/login/ \
  -H "Content-Type: application/json" \
  -d '{"code": "微信登录code"}'
```

### 创建房间
```bash
curl -X POST https://django-9ej9-245877-5-1421749290.sh.run.tcloudbase.com/api/room/create/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"room_name": "好友局", "max_players": 6}'
```

## 小程序配置

在小程序管理后台，需要配置以下服务器域名白名单：

- 合法域名列表添加：
  - `https://django-9ej9-245877-5-1421749290.sh.run.tcloudbase.com` (request 合法域名)
  - `wss://django-9ej9-245877-5-1421749290.sh.run.tcloudbase.com` (socket 合法域名)

## 常见问题

### 1. WebSocket 连接失败
确保微信开发者工具勾选了「不校验合法域名」或已在管理后台配置域名白名单。

### 2. 数据库连接失败
检查云托管环境变量是否正确注入，MySQL 服务是否正常启动。

### 3. 微信登录失败
确认 WECHAT_APPID 和 WECHAT_SECRET 配置正确，且小程序已发布或处于体验版。
