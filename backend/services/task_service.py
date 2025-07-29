import asyncio
import uuid
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from backend.config.settings import settings
from backend.models.schemas import (
    TaskStatus, TaskInfo, ProcessResult, Question, LLMProvider
)
from backend.services.pdf_service import PDFService
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class TaskService:
    """
    任务管理服务
    负责管理文件处理任务的生命周期，包括任务创建、状态跟踪、结果管理等
    """
    
    def __init__(self):
        """初始化任务服务"""
        self.tasks: Dict[str, TaskInfo] = {}  # 内存中的任务存储
        self.pdf_service = PDFService()
        self.llm_service = LLMService()
        
    def create_task(self, filename: str, file_size: int) -> str:
        """
        创建新的处理任务
        
        Args:
            filename: 文件名
            file_size: 文件大小（字节）
            
        Returns:
            str: 任务ID
        """
        task_id = str(uuid.uuid4())
        current_time = datetime.now()
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            filename=filename,
            file_size=file_size,
            created_at=current_time,
            updated_at=current_time,
            progress=0
        )
        
        self.tasks[task_id] = task_info
        logger.info(f"创建任务: {task_id}, 文件: {filename}")
        return task_id
    
    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[TaskInfo]: 任务信息，如果任务不存在则返回None
        """
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          progress: Optional[int] = None,
                          error_message: Optional[str] = None) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度百分比（0-100）
            error_message: 错误信息（如果有）
            
        Returns:
            bool: 更新是否成功
        """
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        task.status = status
        
        if progress is not None:
            task.progress = progress
            
        if error_message:
            task.error_message = error_message
            
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task.completed_at = datetime.now()
            
        logger.info(f"任务 {task_id} 状态更新为: {status.value}")
        return True
    
    async def process_file(self, task_id: str, file_path: str, 
                      provider: LLMProvider,
                      custom_prompt: Optional[str] = None) -> ProcessResult:
        """
        处理PDF文件，提取应用题
        
        Args:
            task_id: 任务ID
            file_path: PDF文件路径
            provider: 大模型提供商
            custom_prompt: 自定义提示词
            
        Returns:
            ProcessResult: 处理结果
        """
        try:
            logger.info(f"开始处理任务 {task_id}: {file_path}")
            
            # 初始化进度
            self.update_task_status(task_id, TaskStatus.PROCESSING, 0)
            
            # 读取文件内容进行验证
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            filename = Path(file_path).name
            
            # 文件验证 (5%)
            self.update_task_status(task_id, TaskStatus.PROCESSING, 5)
            
            if not self.pdf_service.validate_file(file_content, filename):
                error_msg = "无效的PDF文件"
                self.update_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
                
                # 获取任务信息用于构建 ProcessResult
                task_info = self.get_task_info(task_id)
                if not task_info:
                    task_info = TaskInfo(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        filename=filename,
                        file_size=len(file_content),
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        error_message=error_msg
                    )
                
                return ProcessResult(
                    task_info=task_info,
                    questions=[],
                    statistics={"error": error_msg, "total_questions": 0},
                    success=False,
                    error_message=error_msg
                )
            
            # 获取PDF信息 (10%)
            self.update_task_status(task_id, TaskStatus.PROCESSING, 10)
            pdf_info = self.pdf_service.get_pdf_info(file_path)
            total_pages = pdf_info.get('total_pages', 0)
            
            if total_pages == 0:
                error_msg = "无法读取PDF页数，请检查文件格式或安装 poppler"
                self.update_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
                
                task_info = self.get_task_info(task_id)
                return ProcessResult(
                    task_info=task_info,
                    questions=[],
                    statistics={"error": error_msg, "total_questions": 0},
                    success=False,
                    error_message=error_msg
                )
            
            # PDF转换为图片 (15%)
            self.update_task_status(task_id, TaskStatus.PROCESSING, 15)
            image_paths = self.pdf_service.convert_pdf_to_images(file_path, task_id)
            
            if not image_paths:
                error_msg = "PDF转换为图片失败"
                self.update_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
                
                task_info = self.get_task_info(task_id)
                return ProcessResult(
                    task_info=task_info,
                    questions=[],
                    statistics={"error": error_msg, "total_questions": 0},
                    success=False,
                    error_message=error_msg
                )
            
            # 转换完成 (25%)
            self.update_task_status(task_id, TaskStatus.PROCESSING, 25)
            
            # 分析每一页图片 (25% - 95%)
            all_questions = []
            analysis_progress_range = 70  # 分析阶段占70%的进度
            
            for i, image_path in enumerate(image_paths, 1):
                try:
                    # 计算当前页面的进度
                    page_progress = 25 + int((i / len(image_paths)) * analysis_progress_range)
                    self.update_task_status(task_id, TaskStatus.PROCESSING, page_progress)
                    
                    logger.info(f"正在分析第 {i}/{len(image_paths)} 页 (进度: {page_progress}%)")
                    
                    # 分析当前页面
                    questions = await self.llm_service.analyze_image(
                        image_path, provider, filename, custom_prompt
                    )
                    
                    all_questions.extend(questions)
                    logger.info(f"页面 {i}/{len(image_paths)} 分析完成，发现 {len(questions)} 道题")
                    
                except Exception as e:
                    logger.warning(f"页面 {i} 分析失败: {str(e)}")
                    continue
            
            # 清理临时文件 (95%)
            self.update_task_status(task_id, TaskStatus.PROCESSING, 95)
            await self.pdf_service.cleanup_task_files(task_id)
            
            # 完成处理 (100%)
            self.update_task_status(task_id, TaskStatus.COMPLETED, 100)
            
            # 获取最新的任务信息
            task_info = self.get_task_info(task_id)
            
            result = ProcessResult(
                task_info=task_info,
                questions=all_questions,
                statistics={
                    "total_pages": total_pages,
                    "processed_pages": len(image_paths),
                    "skipped_pages": total_pages - len(image_paths),
                    "total_questions": len(all_questions),
                    "success_rate": 100.0
                },
                success=True
            )
            
            # 存储结果到任务信息中
            if task_id in self.tasks:
                self.tasks[task_id].result = result
            
            # 自动导出CSV文件
            try:
                csv_path = self.export_questions_to_csv(task_id)
                logger.info(f"CSV文件已导出到: {csv_path}")
            except Exception as e:
                logger.warning(f"CSV导出失败: {str(e)}")
            
            logger.info(f"任务 {task_id} 处理完成，共处理 {len(image_paths)}/{total_pages} 页，发现 {len(all_questions)} 道题")
            return result
            
        except Exception as e:
            error_msg = f"文件处理失败: {str(e)}"
            logger.error(f"任务 {task_id} 处理失败: {str(e)}", exc_info=True)
            
            # 清理临时文件
            try:
                await self.pdf_service.cleanup_task_files(task_id)
            except Exception:
                pass
            
            self.update_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
            
            # 获取任务信息用于构建 ProcessResult
            task_info = self.get_task_info(task_id)
            if not task_info:
                task_info = TaskInfo(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    filename="unknown",
                    file_size=0,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    error_message=error_msg
                )
            
            return ProcessResult(
                task_info=task_info,
                questions=[],
                statistics={"error": error_msg, "total_questions": 0},
                success=False,
                error_message=error_msg
            )
    
    def get_task_result(self, task_id: str) -> Optional[ProcessResult]:
        """
        获取任务处理结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[ProcessResult]: 处理结果，如果任务不存在或未完成则返回None
        """
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.COMPLETED:
            return None
        return task.result
    
    def list_tasks(self, limit: int = 50) -> List[TaskInfo]:
        """
        获取任务列表
        
        Args:
            limit: 返回任务数量限制
            
        Returns:
            List[TaskInfo]: 任务信息列表，按创建时间倒序排列
        """
        tasks = list(self.tasks.values())
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        return tasks[:limit]
    
    def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 删除是否成功
        """
        if task_id in self.tasks:
            # 清理相关文件
            asyncio.create_task(self.pdf_service.cleanup_task_files(task_id))
            del self.tasks[task_id]
            logger.info(f"删除任务: {task_id}")
            return True
        return False
    
    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        清理过期任务
        
        Args:
            max_age_hours: 任务最大保留时间（小时）
            
        Returns:
            int: 清理的任务数量
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_tasks = [
            task_id for task_id, task in self.tasks.items()
            if task.created_at < cutoff_time
        ]
        
        for task_id in expired_tasks:
            self.delete_task(task_id)
        
        if expired_tasks:
            logger.info(f"清理了 {len(expired_tasks)} 个过期任务")
        
        return len(expired_tasks)

# 全局任务服务实例
task_service = TaskService()

def export_questions_to_csv(self, task_id: str, output_path: Optional[str] = None) -> str:
        """
        将任务中的题目导出为CSV文件
        
        Args:
            task_id: 任务ID
            output_path: 输出文件路径，如果为None则自动生成
            
        Returns:
            str: CSV文件路径
        """
        import csv
        from pathlib import Path
        
        # 获取任务结果
        result = self.get_task_result(task_id)
        if not result or not result.questions:
            raise ValueError(f"任务 {task_id} 没有可导出的题目")
        
        # 生成输出文件路径
        if output_path is None:
            task_info = self.get_task_info(task_id)
            filename = task_info.filename if task_info else "questions"
            # 移除文件扩展名
            filename_without_ext = Path(filename).stem
            output_path = settings.output_path / f"{task_id}_{filename_without_ext}_questions.csv"
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
            # 写入CSV文件
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    '题目ID', '题目内容', '难度等级', '知识点', 
                    '答案', '解题步骤', '来源文件', '置信度'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # 写入表头
                writer.writeheader()
                
                # 写入数据
                for question in result.questions:
                    writer.writerow({
                        '题目ID': question.id,
                        # 移除：'页码': question.page_number,
                        '题目内容': question.content,
                        '难度等级': question.difficulty.value if question.difficulty else '',
                        '知识点': ', '.join(question.knowledge_points) if question.knowledge_points else '',
                        '答案': question.answer if question.answer else '',
                        '解题步骤': question.explanation if question.explanation else '',
                        '来源文件': question.source,
                        '置信度': question.confidence if question.confidence else ''
                    })
        
        logger.info(f"成功导出 {len(result.questions)} 道题目到 {output_path}")
        return str(output_path)