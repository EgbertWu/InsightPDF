from fastapi import APIRouter

from backend.api.v01.endpoints import upload, tasks, health

# 创建 v01 版本的主路由
api_router = APIRouter(prefix="/v01")

# 注册各个端点路由
api_router.include_router(upload.router)
api_router.include_router(tasks.router)
api_router.include_router(health.router)