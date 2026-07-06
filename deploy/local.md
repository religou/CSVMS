# 本地运行指南

## 前置要求

- Python 3.12+
- Node.js 18+
- MySQL 8.0+

## 1. 启动 MySQL 并创建数据库

```sql
CREATE DATABASE csvs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'csvs'@'localhost' IDENTIFIED BY '123456';
GRANT ALL PRIVILEGES ON csvs.* TO 'csvs'@'localhost';
FLUSH PRIVILEGES;
```

## 2. 后端配置

在 `backend/` 目录下创建 `.env` 文件：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=csvs
DB_PASSWORD=123456
DB_NAME=csvs
SECRET_KEY=some-random-secret-key-change-me
DEBUG=true
```

## 3. 安装后端依赖 & 建表

```powershell
cd backend
pip install -r requirements.txt
pip install aiomysql          # 异步 MySQL 驱动
alembic upgrade head
```

如果 alembic 迁移还没生成，可以用 Python 直接建表：

```powershell
python -c "from app.core.database import get_engine, Base; from app.models import *; import asyncio
engine = get_engine()
async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(main())
print('Tables created successfully')"
```

## 4. 启动后端

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

## 5. 安装前端依赖 & 启动

```powershell
cd frontend
npm install   # 首次需要
npm run dev
```

访问 http://localhost:5173 即可使用。

## 地址一览

| 项目     | 地址                         |
| -------- | ---------------------------- |
| 前端     | http://localhost:5173        |
| 后端 API | http://localhost:8000/api/v1 |
| API 文档 | http://localhost:8000/docs   |

## 说明

- 前端 Vite 已配置代理，`/api` 请求会自动转发到后端 8000 端口，无需额外配置 CORS。
- 后端默认 JWT Secret 为 `change-me-in-production`，本地开发可保留，生产环境必须修改。
