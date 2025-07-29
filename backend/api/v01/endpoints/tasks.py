from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from backend.models.schemas import (
    TaskInfo, ProcessResult, StatusResponse, ErrorResponse
)
from backend.services.task_service import task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["任务管理"])

@router.get("/{task_id}/status", response_model=StatusResponse)
async def get_task_status(task_id: str):
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        StatusResponse: 任务状态信息
        
    Raises:
        HTTPException: 任务不存在
    """
    try:
        task_info = task_service.get_task_info(task_id)
        
        if not task_info:
            raise HTTPException(
                status_code=404,
                detail="任务不存在"
            )
        
        return StatusResponse(
            task_id=task_id,
            status=task_info.status,
            progress=task_info.progress,
            filename=task_info.filename,
            file_size=task_info.file_size,
            created_at=task_info.created_at,
            completed_at=task_info.completed_at,
            error_message=task_info.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {task_id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取任务状态失败: {str(e)}"
        )

@router.get("/{task_id}/result", response_model=ProcessResult)
async def get_task_result(task_id: str):
    """
    获取任务处理结果
    
    Args:
        task_id: 任务ID
        
    Returns:
        ProcessResult: 处理结果
        
    Raises:
        HTTPException: 任务不存在或未完成
    """
    try:
        result = task_service.get_task_result(task_id)
        
        if not result:
            task_info = task_service.get_task_info(task_id)
            if not task_info:
                raise HTTPException(
                    status_code=404,
                    detail="任务不存在"
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"任务尚未完成，当前状态: {task_info.status.value}"
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败: {task_id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取任务结果失败: {str(e)}"
        )

@router.get("/", response_model=List[TaskInfo])
async def list_tasks(
    limit: int = Query(50, ge=1, le=100, description="返回任务数量限制")
):
    """
    获取任务列表
    
    Args:
        limit: 返回任务数量限制（1-100）
        
    Returns:
        List[TaskInfo]: 任务信息列表
    """
    try:
        tasks = task_service.list_tasks(limit)
        return tasks
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取任务列表失败: {str(e)}"
        )

@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        dict: 删除结果
        
    Raises:
        HTTPException: 任务不存在
    """
    try:
        success = task_service.delete_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="任务不存在"
            )
        
        return {"message": "任务删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {task_id}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"删除任务失败: {str(e)}"
        )

@router.post("/cleanup")
async def cleanup_old_tasks(
    max_age_hours: int = Query(24, ge=1, le=168, description="任务最大保留时间（小时）")
):
    """
    清理过期任务
    
    Args:
        max_age_hours: 任务最大保留时间（1-168小时）
        
    Returns:
        dict: 清理结果
    """
    try:
        cleaned_count = task_service.cleanup_old_tasks(max_age_hours)
        
        return {
            "message": f"清理完成，删除了 {cleaned_count} 个过期任务",
            "cleaned_count": cleaned_count
        }
        
    except Exception as e:
        logger.error(f"清理过期任务失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"清理过期任务失败: {str(e)}"
        )