from fastapi import APIRouter, HTTPException
from typing import Optional, List
import logging

from backend.models.schemas import (
    CreateAnalysisTaskRequest, CreateAnalysisFromUploadRequest,
    CreateAnalysisTaskResponse, ExecuteAnalysisTaskRequest,
    AnalysisResultResponse, UploadTaskImagesResponse, TaskType
)
from backend.services.task_service import task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["独立分析任务"])

@router.get("/upload-tasks/{task_id}/images", response_model=UploadTaskImagesResponse)
async def get_upload_task_images(task_id: str):
    """
    获取上传任务的图片列表
    
    Args:
        task_id: 上传任务ID
        
    Returns:
        UploadTaskImagesResponse: 图片列表信息
    """
    try:
        result = task_service.get_upload_task_images(task_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
            
        return UploadTaskImagesResponse(
            task_id=result["task_id"],
            filename=result["filename"],
            total_pages=result["total_pages"],
            images=result["images"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取上传任务图片失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取图片列表失败: {str(e)}")


@router.post("/tasks/from-upload", response_model=CreateAnalysisTaskResponse)
async def create_analysis_task_from_upload(request: CreateAnalysisFromUploadRequest):
    """
    从上传任务创建分析任务
    
    Args:
        request: 从上传任务创建分析任务请求
        
    Returns:
        CreateAnalysisTaskResponse: 创建结果
    """
    try:
        # 添加详细的请求参数日志
        logger.info(f"收到创建分析任务请求: {request.dict()}")
        
        # 验证必填参数
        if not request.name or not request.name.strip():
            logger.error("任务名称不能为空")
            raise HTTPException(status_code=422, detail="任务名称不能为空")
            
        if not request.source_upload_task_id or not request.source_upload_task_id.strip():
            logger.error("上传任务ID不能为空")
            raise HTTPException(status_code=422, detail="上传任务ID不能为空")
            
        # 验证provider枚举值
        valid_providers = ["openai", "qwen"]
        if request.provider not in valid_providers:
            logger.error(f"无效的provider: {request.provider}, 有效值: {valid_providers}")
            raise HTTPException(status_code=422, detail=f"无效的provider: {request.provider}")
            
        # 验证selected_image_indices
        if request.selected_image_indices is not None:
            if not isinstance(request.selected_image_indices, list):
                logger.error(f"selected_image_indices必须是列表类型: {type(request.selected_image_indices)}")
                raise HTTPException(status_code=422, detail="selected_image_indices必须是列表类型")
                
            for idx in request.selected_image_indices:
                if not isinstance(idx, int) or idx < 0:
                    logger.error(f"无效的图片索引: {idx}, 必须是非负整数")
                    raise HTTPException(status_code=422, detail=f"无效的图片索引: {idx}")
        
        logger.info(f"参数验证通过，开始创建分析任务")
        
        result = task_service.create_analysis_task_from_upload(request)
        
        if not result["success"]:
            logger.error(f"任务创建失败: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
            
        logger.info(f"分析任务创建成功: {result['task_id']}")
        
        return CreateAnalysisTaskResponse(
            task_id=result["task_id"],
            name=result["name"],
            message="分析任务创建成功",
            total_images=result["total_images"],
            estimated_duration=f"约 {result['total_images'] * 10} 秒"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从上传任务创建分析任务失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建分析任务失败: {str(e)}")

@router.post("/tasks/{task_id}/execute", response_model=AnalysisResultResponse)
async def execute_analysis_task(task_id: str):
    """
    执行分析任务
    
    Args:
        task_id: 分析任务ID
        
    Returns:
        AnalysisResultResponse: 分析结果
    """
    try:
        # 获取任务信息
        task = task_service.get_analysis_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="分析任务不存在")
            
        # 执行分析
        result = await task_service.execute_analysis_task_batch(task_id)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
            
        return AnalysisResultResponse(
            task_id=result["task_id"],
            name=task.name,  # 从task对象获取name
            status=task.status,
            total_images=result["total_images"],
            processed_images=task.processed_images or result["total_images"],  # 使用task对象的processed_images或total_images
            questions=[],  # 暂时返回空列表，因为题目数据在CSV文件中
            statistics={
                "total_images": result["total_images"],
                "total_questions": result["total_questions"],
                "success_rate": 1.0 if result["total_questions"] > 0 else 0.0
            },
            created_at=task.created_at,
            completed_at=task.completed_at,
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行分析任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"执行分析任务失败: {str(e)}")

@router.get("/tasks/{task_id}", response_model=AnalysisResultResponse)
async def get_analysis_task_result(task_id: str):
    """
    获取分析任务结果
    
    Args:
        task_id: 分析任务ID
        
    Returns:
        AnalysisResultResponse: 分析结果
    """
    try:
        task = task_service.get_analysis_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="分析任务不存在")
            
        # 如果任务还未完成，返回当前状态
        questions = []
        statistics = {
            "total_images": len(task.image_paths),
            "total_questions": task.total_questions or 0,
            "success_rate": 0.0
        }
        
        # 如果任务已完成，可以从任务结果中获取更详细信息
        # 这里简化处理，实际项目中可能需要存储分析结果
        
        return AnalysisResultResponse(
            task_id=task.task_id,
            name=task.name,
            status=task.status,
            total_images=len(task.image_paths),
            processed_images=task.processed_images or 0,
            questions=questions,
            statistics=statistics,
            created_at=task.created_at,
            completed_at=task.completed_at,
            success=task.status == TaskStatus.COMPLETED,
            error_message=task.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分析任务结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")

@router.delete("/tasks/{task_id}")
async def delete_analysis_task(task_id: str):
    """
    删除分析任务
    
    Args:
        task_id: 分析任务ID
        
    Returns:
        dict: 删除结果
    """
    try:
        success = task_service.delete_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在")
            
        return {"message": f"分析任务 {task_id} 已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除分析任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")