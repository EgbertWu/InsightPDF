import os
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
import logging

from backend.config.settings import settings
from backend.models.schemas import PDFUploadResponse, ErrorResponse
from backend.services.task_service import task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["文件上传"])

@router.post("/pdf", response_model=PDFUploadResponse)
async def upload_pdf(
    file: UploadFile = File(..., description="要上传的PDF文件")
):
    """
    上传PDF文件并转换为临时图像
    
    Args:
        file: 上传的PDF文件
        
    Returns:
        PDFUploadResponse: 包含任务ID和图像路径的响应
        
    Raises:
        HTTPException: 文件验证失败或处理错误
    """
    try:
        logger.info(f"=== 开始处理PDF上传请求 ===")
        logger.info(f"文件信息: filename={file.filename}, content_type={file.content_type}")
        
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
        
        # 验证文件大小
        content = await file.read()
        file_size = len(content)
        
        logger.info(f"文件大小: {file_size} 字节 ({settings.format_file_size(file_size)})")
        
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
        
        # 创建任务
        task_id = task_service.create_upload_task(file.filename, file_size)
        logger.info(f"任务创建成功: {task_id}")
        
        # 保存文件到临时目录
        os.makedirs(settings.upload_dir, exist_ok=True)
        file_path = os.path.join(settings.upload_dir, f"{task_id}_{file.filename}")
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        logger.info(f"文件保存成功: {file_path}")
        
        # 处理PDF转换
        result = await task_service.upload_and_convert_pdf(task_id, file_path)
        
        # 删除原始PDF文件
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"删除临时PDF文件失败: {file_path}, 错误: {str(e)}")
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )
        
        response = PDFUploadResponse(
            task_id=task_id,
            message="PDF上传和转换成功",
            filename=file.filename,
            file_size=settings.format_file_size(file_size),
            total_pages=result["total_pages"],
            image_paths=result["image_paths"],
            temp_dir=result["temp_dir"]
        )
        
        logger.info(f"PDF上传转换成功: {file.filename}, 任务ID: {task_id}")
        return response
        
    except HTTPException as he:
        logger.error(f"HTTP异常: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        logger.error(f"PDF上传失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"PDF上传失败: {str(e)}"
        )