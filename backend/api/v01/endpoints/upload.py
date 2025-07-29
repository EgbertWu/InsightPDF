import os
import aiofiles
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from backend.config.settings import settings
from backend.models.schemas import (
    UploadResponse, LLMProvider, ErrorResponse
)
from backend.services.task_service import task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["文件上传"])

@router.post("/", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="要上传的PDF文件"),
    provider: LLMProvider = Form(..., description="大模型提供商"),
    custom_prompt: Optional[str] = Form(None, description="自定义提示词")
):
    """
    上传PDF文件并开始处理
    
    Args:
        background_tasks: FastAPI后台任务
        file: 上传的PDF文件
        provider: 大模型提供商（openai 或 qwen）
        custom_prompt: 自定义提示词（可选）
        
    Returns:
        UploadResponse: 包含任务ID的响应
        
    Raises:
        HTTPException: 文件验证失败或处理错误
    """
    try:
        # 添加详细的调试信息
        logger.info(f"=== 开始处理上传请求 ===")
        logger.info(f"文件信息: filename={file.filename}, content_type={file.content_type}")
        logger.info(f"提供商: {provider}")
        logger.info(f"自定义提示词: {custom_prompt}")
        
        # 验证文件类型
        if not file.filename:
            logger.error("文件名为空")
            raise HTTPException(
                status_code=400,
                detail="文件名不能为空"
            )
            
        if not file.filename.lower().endswith('.pdf'):
            logger.error(f"不支持的文件类型: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="只支持PDF文件格式"
            )
        
        logger.info("文件类型验证通过")
        
        # 验证文件大小
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        logger.info(f"文件大小: {file_size} 字节 ({settings.format_file_size(file_size)})")
        logger.info(f"最大允许大小: {settings.max_file_size_bytes} 字节 ({settings.format_file_size(settings.max_file_size_bytes)})")
        
        if file_size > settings.max_file_size_bytes:
            logger.error(f"文件大小超过限制: {file_size} > {settings.max_file_size_bytes}")
            raise HTTPException(
                status_code=413,
                detail=f"文件大小超过限制（最大 {settings.format_file_size(settings.max_file_size_bytes)}）"
            )
        
        if file_size == 0:
            logger.error("文件为空")
            raise HTTPException(
                status_code=400,
                detail="文件为空"
            )
        
        logger.info("文件大小验证通过")
        
        # 验证提供商
        try:
            provider_value = LLMProvider(provider)
            logger.info(f"提供商验证通过: {provider_value}")
        except ValueError as e:
            logger.error(f"无效的提供商: {provider}, 错误: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"无效的大模型提供商: {provider}"
            )
        
        # 创建任务
        logger.info("开始创建任务")
        task_id = task_service.create_task(file.filename, file_size)
        logger.info(f"任务创建成功: {task_id}")
        
        # 保存文件到临时目录
        logger.info(f"开始保存文件到: {settings.upload_dir}")
        os.makedirs(settings.upload_dir, exist_ok=True)
        file_path = os.path.join(settings.upload_dir, f"{task_id}_{file.filename}")
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"文件保存成功: {file_path}")
        
        # 在后台处理文件
        logger.info("添加后台任务")
        background_tasks.add_task(
            process_file_background,
            task_id,
            file_path,
            provider_value,
            custom_prompt
        )
        
        logger.info(f"文件上传成功: {file.filename}, 任务ID: {task_id}")
        
        response = UploadResponse(
            task_id=task_id,
            message="文件上传成功，正在处理中",
            filename=file.filename,
            file_size=settings.format_file_size(file_size)
        )
        
        logger.info(f"返回响应: {response}")
        return response
        
    except HTTPException as he:
        logger.error(f"HTTP异常: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"文件上传失败: {str(e)}"
        )

async def process_file_background(
    task_id: str,
    file_path: str,
    provider: LLMProvider,
    custom_prompt: Optional[str] = None
):
    """
    后台处理文件的任务函数
    
    Args:
        task_id: 任务ID
        file_path: 文件路径
        provider: 大模型提供商
        custom_prompt: 自定义提示词
    """
    try:
        # 调用任务服务处理文件
        result = await task_service.process_file(
            task_id, file_path, provider, custom_prompt
        )
        
        # 删除临时文件
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"删除临时文件失败: {file_path}, 错误: {str(e)}")
        
        logger.info(f"后台任务完成: {task_id}, 成功: {result.success}")
        
    except Exception as e:
        logger.error(f"后台任务失败: {task_id}, 错误: {str(e)}", exc_info=True)
        
        # 删除临时文件
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass