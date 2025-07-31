import asyncio
import uuid
import os
import json  # 新增：用于JSON文件操作
import csv   # 新增：用于CSV文件操作
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from backend.config.settings import settings
from backend.models.schemas import (
    TaskType, TaskStatus, UploadTaskInfo, AnalysisTaskInfo, TaskInfo,
    Question, LLMProvider, CreateAnalysisTaskRequest, CreateAnalysisFromUploadRequest
)
from backend.services.pdf_service import PDFService
from backend.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class TaskService:
    """
    重构后的任务管理服务
    支持独立的上传任务和分析任务管理
    """
    
    def __init__(self):
        """初始化任务服务"""
        self.upload_tasks: Dict[str, UploadTaskInfo] = {}  # 上传任务存储
        self.analysis_tasks: Dict[str, AnalysisTaskInfo] = {}  # 分析任务存储
        self.pdf_service = PDFService()
        self.llm_service = LLMService()
        
        # 数据文件路径
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)  # 确保数据目录存在
        self.tasks_file = self.data_dir / "tasks.json"
        
        # 启动时加载已存在的任务数据
        self._load_tasks_from_file()
        
    def _save_tasks_to_file(self):
        """
        保存任务数据到JSON文件
        
        改动原因：实现任务数据持久化，防止服务器重启后数据丢失
        """
        try:
            # 准备要保存的数据
            data = {
                "upload_tasks": {},
                "analysis_tasks": {},
                "saved_at": datetime.now().isoformat()
            }
            
            # 转换上传任务为可序列化格式
            for task_id, task_info in self.upload_tasks.items():
                data["upload_tasks"][task_id] = task_info.dict()
                
            # 转换分析任务为可序列化格式
            for task_id, task_info in self.analysis_tasks.items():
                data["analysis_tasks"][task_id] = task_info.dict()
            
            # 写入文件
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                
            logger.info(f"任务数据已保存到文件: {self.tasks_file}")
            
        except Exception as e:
            logger.error(f"保存任务数据失败: {str(e)}")
            
    def _load_tasks_from_file(self):
        """
        从JSON文件加载任务数据
        
        改动原因：服务器启动时恢复之前保存的任务数据
        """
        try:
            if not self.tasks_file.exists():
                logger.info("任务数据文件不存在，使用空数据开始")
                return
                
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 恢复上传任务
            upload_tasks_data = data.get("upload_tasks", {})
            for task_id, task_data in upload_tasks_data.items():
                try:
                    # 转换日期字符串为datetime对象
                    if isinstance(task_data.get('created_at'), str):
                        task_data['created_at'] = datetime.fromisoformat(task_data['created_at'])
                    if isinstance(task_data.get('updated_at'), str):
                        task_data['updated_at'] = datetime.fromisoformat(task_data['updated_at'])
                    if task_data.get('completed_at') and isinstance(task_data['completed_at'], str):
                        task_data['completed_at'] = datetime.fromisoformat(task_data['completed_at'])
                        
                    self.upload_tasks[task_id] = UploadTaskInfo(**task_data)
                except Exception as e:
                    logger.warning(f"恢复上传任务 {task_id} 失败: {str(e)}")
                    
            # 恢复分析任务
            analysis_tasks_data = data.get("analysis_tasks", {})
            for task_id, task_data in analysis_tasks_data.items():
                try:
                    # 转换日期字符串为datetime对象
                    if isinstance(task_data.get('created_at'), str):
                        task_data['created_at'] = datetime.fromisoformat(task_data['created_at'])
                    if isinstance(task_data.get('updated_at'), str):
                        task_data['updated_at'] = datetime.fromisoformat(task_data['updated_at'])
                    if task_data.get('completed_at') and isinstance(task_data['completed_at'], str):
                        task_data['completed_at'] = datetime.fromisoformat(task_data['completed_at'])
                        
                    self.analysis_tasks[task_id] = AnalysisTaskInfo(**task_data)
                except Exception as e:
                    logger.warning(f"恢复分析任务 {task_id} 失败: {str(e)}")
                    
            logger.info(f"成功加载 {len(self.upload_tasks)} 个上传任务和 {len(self.analysis_tasks)} 个分析任务")
            
        except Exception as e:
            logger.error(f"加载任务数据失败: {str(e)}")
    
    # ==================== 上传任务管理 ====================
    
    def create_upload_task(self, filename: str, file_size: int, user_id: Optional[str] = None) -> str:
        """
        创建PDF上传任务
        
        Args:
            filename: 文件名
            file_size: 文件大小（字节）
            user_id: 用户ID（未来扩展）
            
        Returns:
            str: 上传任务ID
        """
        task_id = str(uuid.uuid4())
        current_time = datetime.now()
        
        task_info = UploadTaskInfo(
            task_id=task_id,
            user_id=user_id,
            status=TaskStatus.PENDING,
            filename=filename,
            file_size=file_size,
            created_at=current_time,
            updated_at=current_time,
            progress=0
        )
        
        self.upload_tasks[task_id] = task_info
        
        # 自动保存到文件
        self._save_tasks_to_file()
        
        logger.info(f"创建上传任务: {task_id}, 文件: {filename}")
        return task_id
    
    def get_upload_task(self, task_id: str) -> Optional[UploadTaskInfo]:
        """
        获取上传任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[UploadTaskInfo]: 任务信息
        """
        return self.upload_tasks.get(task_id)
    
    def update_upload_task_status(self, task_id: str, status: TaskStatus, 
                                progress: Optional[int] = None,
                                error_message: Optional[str] = None,
                                **kwargs) -> bool:
        """
        更新上传任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度（0-100）
            error_message: 错误信息
            **kwargs: 其他要更新的字段
            
        Returns:
            bool: 是否更新成功
        """
        if task_id not in self.upload_tasks:
            return False
            
        task = self.upload_tasks[task_id]
        task.status = status
        task.updated_at = datetime.now()
        
        if progress is not None:
            task.progress = progress
        if error_message is not None:
            task.error_message = error_message
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()
            
        # 更新其他字段
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
                
        # 自动保存到文件
        self._save_tasks_to_file()
                
        return True
        
    def update_analysis_task_status(self, task_id: str, status: TaskStatus,
                                  progress: Optional[int] = None,
                                  error_message: Optional[str] = None,
                                  **kwargs) -> bool:
        """
        更新分析任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度（0-100）
            error_message: 错误信息
            **kwargs: 其他要更新的字段
            
        Returns:
            bool: 是否更新成功
        """
        if task_id not in self.analysis_tasks:
            return False
            
        task = self.analysis_tasks[task_id]
        task.status = status
        task.updated_at = datetime.now()
        
        if progress is not None:
            task.progress = progress
        if error_message is not None:
            task.error_message = error_message
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()
            
        # 更新其他字段
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
                
        # 自动保存到文件
        self._save_tasks_to_file()
                
        return True
    
    async def upload_and_convert_pdf(self, task_id: str, file_path: str) -> Dict[str, Any]:
        """
        执行PDF上传和转换任务
        
        Args:
            task_id: 任务ID
            file_path: PDF文件路径
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            logger.info(f"开始处理PDF上传任务 {task_id}")
            
            # 验证任务存在
            task = self.get_upload_task(task_id)
            if not task:
                return {"success": False, "error": "任务不存在"}
            
            # 更新状态为处理中
            self.update_upload_task_status(task_id, TaskStatus.PROCESSING, 0)

            filename = Path(file_path).name
            
            # 验证PDF文件
            if not self.pdf_service.validate_file(file_path, filename):
                error_msg = "无效的PDF文件"
                self.update_upload_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
                return {"success": False, "error": error_msg}
            
            # 获取PDF信息
            self.update_upload_task_status(task_id, TaskStatus.PROCESSING, 10)
            pdf_info = self.pdf_service.get_pdf_info(file_path)
            total_pages = pdf_info["total_pages"]
            
            # 更新任务信息
            self.update_upload_task_status(
                task_id, TaskStatus.PROCESSING, 20,
                total_pages=total_pages
            )
            
            # 转换PDF为图片
            logger.info(f"开始转换PDF为图片，总页数: {total_pages}")
            result = self.pdf_service.convert_pdf_to_temp_images(
                file_path, task_id
            )
            
            if not result["success"]:
                error_msg = result["error"]
                self.update_upload_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
                return {"success": False, "error": error_msg}
            
            # 更新任务完成信息
            image_paths = result["image_paths"]
            output_dir = result["temp_dir"]  # 改为 temp_dir
            
            self.update_upload_task_status(
                task_id, TaskStatus.COMPLETED, 100,
                processed_pages=len(image_paths),
                output_dir=output_dir,
                image_paths=image_paths
            )
            
            logger.info(f"PDF上传任务完成: {task_id}, 生成 {len(image_paths)} 张图片")
            
            return {
                "success": True,
                "task_id": task_id,
                "total_pages": total_pages,
                "image_paths": image_paths,
                "temp_dir": output_dir  # 改为 temp_dir
            }
            
        except Exception as e:
            error_msg = f"PDF处理失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.update_upload_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
            return {"success": False, "error": error_msg}
    
    def get_upload_task_images(self, task_id: str) -> Dict[str, Any]:
        """
        获取上传任务的图片列表
        
        Args:
            task_id: 上传任务ID
            
        Returns:
            Dict[str, Any]: 图片信息
        """
        task = self.get_upload_task(task_id)
        if not task:
            return {"success": False, "error": "任务不存在"}
            
        if task.status != TaskStatus.COMPLETED:
            return {"success": False, "error": "任务未完成"}
            
        if not task.image_paths:
            return {"success": False, "error": "没有找到图片文件"}
            
        images = []
        for i, image_path in enumerate(task.image_paths):
            image_info = {
                "index": i,
                "path": image_path,
                "page_number": i + 1,
                "filename": Path(image_path).name
            }
            
            # 获取文件大小
            try:
                image_info["size"] = os.path.getsize(image_path)
            except:
                image_info["size"] = 0
                
            images.append(image_info)
            
        return {
            "success": True,
            "task_id": task_id,
            "filename": task.filename,
            "total_pages": task.total_pages or len(images),
            "images": images
        }
    
    # ==================== 分析任务管理 ====================
    
    def create_analysis_task(self, request: CreateAnalysisTaskRequest, user_id: Optional[str] = None) -> str:
        """
        创建分析任务
        
        Args:
            request: 创建分析任务请求
            user_id: 用户ID（未来扩展）
            
        Returns:
            str: 任务ID
        """
        task_id = str(uuid.uuid4())
        
        # 创建分析任务信息
        task_info = AnalysisTaskInfo(
            task_id=task_id,
            task_type=TaskType.IMAGE_ANALYSIS,
            user_id=user_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            name=request.name,
            description=request.description,
            source_upload_task_id=request.source_upload_task_id,
            image_paths=request.image_paths,
            provider=request.provider,
            custom_prompt=request.custom_prompt,
            extract_answers=request.extract_answers,
            extract_knowledge_points=request.extract_knowledge_points,
            output_format=request.output_format
        )
        
        # 存储任务
        self.analysis_tasks[task_id] = task_info
        
        # 保存到文件
        self._save_tasks_to_file()
        
        logger.info(f"创建分析任务成功: {task_id}, 名称: {request.name}, 图片数量: {len(request.image_paths)}")
        
        return task_id
    
    def create_analysis_task_from_upload(self, request: CreateAnalysisFromUploadRequest,
                                       user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        从上传任务创建分析任务
        
        Args:
            request: 从上传任务创建分析任务请求
            user_id: 用户ID（未来扩展）
            
        Returns:
            Dict[str, Any]: 创建结果
        """
        # 获取上传任务信息
        upload_task = self.get_upload_task(request.source_upload_task_id)
        if not upload_task:
            return {"success": False, "error": "上传任务不存在"}
            
        if upload_task.status != TaskStatus.COMPLETED:
            return {"success": False, "error": "上传任务未完成"}
            
        if not upload_task.image_paths:
            return {"success": False, "error": "上传任务没有生成图片"}
            
        # 选择要分析的图片
        if request.selected_image_indices:
            # 验证索引有效性
            max_index = len(upload_task.image_paths) - 1
            invalid_indices = [i for i in request.selected_image_indices if i < 0 or i > max_index]
            if invalid_indices:
                return {"success": False, "error": f"无效的图片索引: {invalid_indices}"}
                
            selected_image_paths = [upload_task.image_paths[i] for i in request.selected_image_indices]
        else:
            # 选择所有图片
            selected_image_paths = upload_task.image_paths
            
        # 创建分析任务请求
        analysis_request = CreateAnalysisTaskRequest(
            name=request.name,
            description=request.description,
            image_paths=selected_image_paths,
            provider=request.provider,
            custom_prompt=request.custom_prompt,
            extract_answers=request.extract_answers,
            extract_knowledge_points=request.extract_knowledge_points,
            output_format=request.output_format,
            source_upload_task_id=request.source_upload_task_id
        )
        
        # 创建分析任务
        task_id = self.create_analysis_task(analysis_request, user_id)
        
        return {
            "success": True,
            "task_id": task_id,
            "name": request.name,
            "total_images": len(selected_image_paths),
            "source_upload_task_id": request.source_upload_task_id
        }
    
    def get_analysis_task(self, task_id: str) -> Optional[AnalysisTaskInfo]:
        """
        获取分析任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[AnalysisTaskInfo]: 任务信息
        """
        return self.analysis_tasks.get(task_id)
    
    def update_analysis_task_status(self, task_id: str, status: TaskStatus,
                                  progress: Optional[int] = None,
                                  error_message: Optional[str] = None,
                                  **kwargs) -> bool:
        """
        更新分析任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度（0-100）
            error_message: 错误信息
            **kwargs: 其他要更新的字段
            
        Returns:
            bool: 是否更新成功
        """
        if task_id not in self.analysis_tasks:
            return False
            
        task = self.analysis_tasks[task_id]
        task.status = status
        task.updated_at = datetime.now()
        
        if progress is not None:
            task.progress = progress
        if error_message is not None:
            task.error_message = error_message
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()
            
        # 更新其他字段
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
                
        return True
    
    async def execute_analysis_task_batch(self, task_id: str, batch_size: int = 10) -> Dict[str, Any]:
        """
        分批执行分析任务
        
        Args:
            task_id: 分析任务ID
            batch_size: 每批处理的图片数量
            
        改动原因：优化大批量数据处理，避免内存溢出和长时间阻塞
        """
        try:
            task = self.get_analysis_task(task_id)
            if not task:
                return {"success": False, "error": "分析任务不存在"}
            
            total_images = len(task.image_paths)
            all_questions_count = 0
            
            # 初始化CSV文件
            csv_path = self._initialize_csv_file(task_id, task.name)
            
            # 分批处理
            for batch_start in range(0, total_images, batch_size):
                batch_end = min(batch_start + batch_size, total_images)
                batch_images = task.image_paths[batch_start:batch_end]
                
                logger.info(f"处理批次 {batch_start//batch_size + 1}: 图片 {batch_start+1}-{batch_end}")
                
                # 处理当前批次
                batch_questions = []
                for i, image_path in enumerate(batch_images):
                    try:
                        questions = await self.llm_service.analyze_image(
                            image_path, task.provider, 
                            Path(image_path).name, task.custom_prompt
                        )
                        batch_questions.extend(questions)
                        
                        # 更新进度
                        progress = int(((batch_start + i + 1) / total_images) * 90)
                        self.update_analysis_task_status(task_id, TaskStatus.PROCESSING, progress)
                        
                    except Exception as e:
                        logger.warning(f"图片 {batch_start + i + 1} 分析失败: {str(e)}")
                        continue
                    
                # 追加写入CSV（而不是累积在内存中）
                self._append_questions_to_csv(csv_path, batch_questions)
                all_questions_count += len(batch_questions)
                
                logger.info(f"批次完成，本批识别 {len(batch_questions)} 道题")
                
                # 可选：批次间短暂休息，避免API限流
                await asyncio.sleep(1)
            
            # 任务完成
            self.update_analysis_task_status(
                task_id, TaskStatus.COMPLETED, 100,
                total_questions=all_questions_count,
                processed_images=total_images
            )
            
            return {
                "success": True,
                "task_id": task_id,
                "total_images": total_images,
                "total_questions": all_questions_count,
                "csv_path": csv_path
            }
            
        except Exception as e:
            logger.error(f"分批分析任务失败: {str(e)}")
            self.update_analysis_task_status(task_id, TaskStatus.FAILED, error_message=str(e))
            return {"success": False, "error": str(e)}
    
    def _initialize_csv_file(self, task_id: str, task_name: str) -> str:
        """
        初始化CSV文件，写入表头
        
        改动原因：支持分批写入，避免重复写入表头
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{task_name}_{task_id[:8]}_{timestamp}_questions.csv"
        output_dir = Path("outputs")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename
        
        # 写入表头
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                '题目ID', '题目内容', '难度等级', '知识点', 
                '答案', '解析', '来源文件', '置信度'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        
        return str(output_path)
    
    def _append_questions_to_csv(self, csv_path: str, questions: List[Question]):
        """
        追加题目到CSV文件
        
        改动原因：支持分批写入，避免内存累积
        """
        with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                '题目ID', '题目内容', '难度等级', '知识点', 
                '答案', '解析', '来源文件', '置信度'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            for question in questions:
                writer.writerow({
                    '题目ID': question.id,
                    '题目内容': question.content,
                    '难度等级': question.difficulty.value if question.difficulty else '',
                    '知识点': ', '.join(question.knowledge_points) if question.knowledge_points else '',
                    '答案': question.answer if question.answer else '',
                    '解析': question.explanation if question.explanation else '',
                    '来源文件': question.source,
                    '置信度': question.confidence if question.confidence else ''
                })


# 全局任务服务实例
task_service = TaskService()


