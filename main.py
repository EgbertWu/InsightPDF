import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from backend.config.settings import settings
from backend.api.v01.router import api_router
from backend.services.task_service import task_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    在应用启动和关闭时执行必要的初始化和清理工作
    """
    # 启动时的初始化工作
    logger.info("应用启动中...")
    
    # 确保必要的目录存在
    import os
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)
    
    logger.info(f"上传目录: {settings.upload_dir}")
    logger.info(f"输出目录: {settings.output_dir}")
    logger.info(f"最大文件大小: {settings.format_file_size(settings.max_file_size_bytes)}")
    
    # 检查大模型配置
    openai_config = settings.get_llm_config("openai")
    qwen_config = settings.get_llm_config("qwen")
    
    if openai_config and openai_config.get("api_key"):
        logger.info("OpenAI 配置已加载")
    else:
        logger.warning("OpenAI 配置未找到或不完整")
    
    if qwen_config and qwen_config.get("api_key"):
        logger.info("通义千问 配置已加载")
    else:
        logger.warning("通义千问 配置未找到或不完整")
    
    logger.info("应用启动完成")
    
    yield
    
    # 关闭时的清理工作
    logger.info("应用关闭中...")
    
    # 清理过期任务
    try:
        cleaned_count = task_service.cleanup_old_tasks(24)
        logger.info(f"清理了 {cleaned_count} 个过期任务")
    except Exception as e:
        logger.error(f"清理任务失败: {str(e)}")
    
    logger.info("应用已关闭")

# 创建 FastAPI 应用实例
app = FastAPI(
    title="InsightPDF API",
    description="PDF 应用题识别和提取 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    全局异常处理器
    捕获未处理的异常并返回统一的错误响应
    """
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "message": "服务器遇到了一个错误，请稍后重试",
            "detail": str(exc) if settings.debug else None
        }
    )

# 注册 API 路由
app.include_router(api_router, prefix="/api")

# 根路径重定向到文档
@app.get("/")
async def root():
    """
    根路径，返回 API 基本信息
    """
    return {
        "message": "InsightPDF API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v01/health"
    }

if __name__ == "__main__":
    # 开发环境启动配置
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )