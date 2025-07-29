from fastapi import APIRouter, HTTPException
import logging
import os
from datetime import datetime

from backend.config.settings import settings
from backend.models.schemas import HealthResponse
from backend.services.task_service import task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["健康检查"])

@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    系统健康检查
    
    Returns:
        HealthResponse: 系统健康状态
    """
    try:
        # 检查必要目录是否存在
        upload_dir_exists = os.path.exists(settings.upload_dir)
        output_dir_exists = os.path.exists(settings.output_dir)
        
        # 检查任务服务状态
        task_count = len(task_service.tasks)
        
        # 检查配置
        config_status = {
            "upload_dir": settings.upload_dir,
            "upload_dir_exists": upload_dir_exists,
            "output_dir": settings.output_dir,
            "output_dir_exists": output_dir_exists,
            "max_file_size": settings.format_file_size(settings.max_file_size_bytes),
            "api_timeout": f"{settings.api_timeout_seconds}秒"
        }
        
        # 检查大模型配置
        llm_config = {}
        openai_config = settings.get_llm_config("openai")
        qwen_config = settings.get_llm_config("qwen")
        
        if openai_config:
            llm_config["openai"] = {
                "configured": bool(openai_config.get("api_key")),
                "base_url": openai_config.get("base_url", "默认")
            }
        
        if qwen_config:
            llm_config["qwen"] = {
                "configured": bool(qwen_config.get("api_key")),
                "base_url": qwen_config.get("base_url", "默认")
            }
        
        # 判断整体健康状态
        is_healthy = (
            upload_dir_exists and 
            output_dir_exists and 
            (llm_config.get("openai", {}).get("configured", False) or 
             llm_config.get("qwen", {}).get("configured", False))
        )
        
        return HealthResponse(
            status="healthy" if is_healthy else "unhealthy",
            timestamp=datetime.now(),
            version="1.0.0",
            uptime="运行中",
            task_count=task_count,
            config=config_status,
            llm_providers=llm_config
        )
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )