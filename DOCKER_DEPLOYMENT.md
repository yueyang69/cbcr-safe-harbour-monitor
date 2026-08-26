# CbCR Safe Harbour - Docker Deployment Guide

## 快速开始

### 方式 1: 使用启动脚本（推荐）

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

### 方式 2: 手动启动

1. **创建环境配置文件**
```bash
cp .env.example .env
# 编辑 .env 文件，配置 MINIMAX_API_KEY（可选）
```

2. **构建并启动服务**
```bash
docker-compose up -d --build
```

3. **查看服务状态**
```bash
docker-compose ps
```

## 访问应用

- **前端界面**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **数据库**: localhost:5432 (用户名: cbcr, 密码: cbcr_dev_only)

## 测试用户角色

系统使用简单的角色认证，通过 HTTP Header 模拟不同用户：

- **分部员工**: `X-User-Role: subsidiary` - 只能录入数据
- **总部用户**: `X-User-Role: hq` - 可以配置映射和查看 Dashboard
- **管理员**: `X-User-Role: admin` - 完全权限

前端默认使用 localStorage 存储角色，可在浏览器开发者工具中切换：
```javascript
localStorage.setItem('user_role', 'hq')
```

## AI 功能配置

系统支持两种模式：

### 1. Mock 模式（默认）
不需要配置 API Key，AI 功能会返回硬编码的模拟响应：
- 字段映射使用硬编码字典
- 异常检测使用确定性规则
- 简报生成使用模板

### 2. 真实 AI 模式
在 `.env` 文件中配置：
```bash
MINIMAX_API_KEY=sk-your-actual-key-here
MINIMAX_API_BASE=https://api.minimaxi.com/v1
```

系统会自动检测 API Key 是否有效，无效时自动降级到 Mock 模式。

## 常用命令

```bash
# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f api
docker-compose logs -f web

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 停止并清除数据
docker-compose down -v

# 重新构建
docker-compose build --no-cache
docker-compose up -d
```

## 数据库管理

### 连接数据库
```bash
docker-compose exec db psql -U cbcr -d cbcr
```

### 运行数据库迁移
```bash
# 进入后端容器
docker-compose exec api bash

# 查看迁移状态
alembic current

# 运行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 故障排查

### 服务无法启动
```bash
# 检查端口占用
netstat -ano | findstr "5432 8000 5173"  # Windows
lsof -i :5432,8000,5173                  # Linux/Mac

# 查看详细错误日志
docker-compose logs --tail=50 api
```

### 数据库连接失败
```bash
# 检查数据库健康状态
docker-compose exec db pg_isready -U cbcr

# 重启数据库
docker-compose restart db
```

### 前端无法连接后端
检查 `.env` 文件中的 `VITE_API_BASE_URL` 配置：
- 本地开发: `http://localhost:8000/api/v1`
- 远程部署: `http://your-server-ip:8000/api/v1`

## 生产部署注意事项

1. **修改默认密码**
   ```bash
   POSTGRES_PASSWORD=your_secure_password_here
   ```

2. **配置 CORS**
   ```bash
   CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com
   ```

3. **使用 HTTPS**
   添加 Nginx 反向代理或使用 Traefik

4. **配置真实 API Key**
   ```bash
   MINIMAX_API_KEY=sk-your-production-key
   ```

5. **数据备份**
   ```bash
   docker-compose exec db pg_dump -U cbcr cbcr > backup.sql
   ```

## 架构说明

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Frontend  │─────▶│   Backend   │─────▶│  PostgreSQL │
│   (React)   │      │  (FastAPI)  │      │   Database  │
│  Port 5173  │      │  Port 8000  │      │  Port 5432  │
└─────────────┘      └─────────────┘      └─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │  MiniMax AI │
                     │     API     │
                     │  (Optional) │
                     └─────────────┘
```

## 技术栈

- **前端**: React 18 + TypeScript + Vite + Tailwind CSS
- **后端**: Python 3.12 + FastAPI + SQLAlchemy (异步)
- **数据库**: PostgreSQL 16
- **AI**: MiniMax API (可选，有 Mock 降级)
- **容器**: Docker + Docker Compose

## 支持

遇到问题？请检查：
1. Docker 和 Docker Compose 版本是否最新
2. 端口是否被占用
3. 查看服务日志 `docker-compose logs -f`
