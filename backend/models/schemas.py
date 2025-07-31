from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TaskType(str, Enum):
    """任务类型枚举"""
    PDF_UPLOAD = "pdf_upload"      # PDF上传转换任务
    IMAGE_ANALYSIS = "image_analysis"  # 图片分析任务

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"   # 已取消

class LLMProvider(str, Enum):
    """大模型提供商枚举"""
    OPENAI = "openai"
    QWEN = "qwen"

class DifficultyLevel(str, Enum):
    """难度等级枚举"""
    EASY = "easy"        # 简单
    MEDIUM = "medium"    # 中等
    HARD = "hard"        # 困难

# 基础任务信息
class BaseTaskInfo(BaseModel):
    """基础任务信息模型"""
    task_id: str = Field(..., description="任务ID")
    task_type: TaskType = Field(..., description="任务类型")
    user_id: Optional[str] = Field(None, description="用户ID（未来扩展）")
    status: TaskStatus = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    progress: Optional[float] = Field(None, description="处理进度（0-100）")

# PDF上传任务信息
class UploadTaskInfo(BaseTaskInfo):
    """PDF上传任务信息模型"""
    task_type: TaskType = Field(TaskType.PDF_UPLOAD, description="任务类型")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    total_pages: Optional[int] = Field(None, description="总页数")
    processed_pages: Optional[int] = Field(None, description="已处理页数")
    output_dir: Optional[str] = Field(None, description="输出目录路径")
    image_paths: Optional[List[str]] = Field(None, description="生成的图片路径列表")

# 分析任务信息
class AnalysisTaskInfo(BaseTaskInfo):
    """分析任务信息模型"""
    task_type: TaskType = Field(TaskType.IMAGE_ANALYSIS, description="任务类型")
    name: str = Field(..., description="分析任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    source_upload_task_id: Optional[str] = Field(None, description="来源上传任务ID")
    image_paths: List[str] = Field(..., description="要分析的图片路径列表")
    provider: LLMProvider = Field(..., description="大模型提供商")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    extract_answers: bool = Field(True, description="是否提取答案")
    extract_knowledge_points: bool = Field(True, description="是否提取考点")
    output_format: str = Field("json", description="输出格式")
    total_questions: Optional[int] = Field(None, description="识别的题目总数")
    processed_images: Optional[int] = Field(None, description="已处理图片数")

# 统一的任务信息（用于API响应）
# 删除第113-128行的重复TaskInfo定义
# 保留第71-80行的TaskInfo定义
class TaskInfo(BaseModel):
    """统一任务信息模型（用于API响应）"""
    task_id: str = Field(..., description="任务ID")
    task_type: TaskType = Field(..., description="任务类型")
    status: TaskStatus = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    progress: Optional[float] = Field(None, description="处理进度（0-100）")
    # 使用details字段包含所有具体信息，避免字段冲突
    details: Dict[str, Any] = Field(..., description="任务详细信息")

class UploadRequest(BaseModel):
    """
    PDF文件上传请求模型（仅上传和转换功能）
    更新原因：将上传和分析功能分离，此模型只负责PDF上传转换相关参数
    """
    convert_dpi: int = Field(300, description="PDF转图像的DPI设置")
    skip_blank_pages: bool = Field(True, description="是否跳过空白页")
    max_pages: Optional[int] = Field(None, description="最大处理页数限制")

class ProcessRequest(BaseModel):
    """
    处理请求模型（保持不变，用于兼容旧接口）
    """
    task_id: str = Field(..., description="任务ID")
    llm_provider: LLMProvider = Field(..., description="大模型提供商")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")

# 响应模型
class Question(BaseModel):
    """
    应用题模型
    """
    id: int = Field(..., description="题目序号")
    content: str = Field(..., description="题目内容")
    answer: Optional[str] = Field(None, description="答案")
    explanation: Optional[str] = Field(None, description="解析")
    knowledge_points: Optional[List[str]] = Field(None, description="考点")
    difficulty: Optional[DifficultyLevel] = Field(None, description="难度等级")
    source: Optional[str] = Field(None, description="来源")
    confidence: Optional[float] = Field(None, description="识别置信度")

class TaskInfo(BaseModel):
    """
    任务信息模型
    """
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    total_pages: Optional[int] = Field(None, description="总页数")
    processed_pages: Optional[int] = Field(None, description="已处理页数")
    total_questions: Optional[int] = Field(None, description="题目总数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    progress: Optional[float] = Field(None, description="处理进度（0-100）")

class ProcessResult(BaseModel):
    """
    处理结果模型
    """
    task_info: TaskInfo = Field(..., description="任务信息")
    questions: List[Question] = Field(..., description="应用题列表")
    statistics: Dict[str, Any] = Field(..., description="统计信息")
    output_files: Optional[List[str]] = Field(None, description="输出文件路径")
    success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")

# 新的分离式接口响应模型
class UploadResponse(BaseModel):
    """
    通用文件上传响应模型
    """
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="响应消息")
    filename: str = Field(..., description="文件名")
    file_size: str = Field(..., description="文件大小")

class PDFUploadResponse(BaseModel):
    """
    PDF上传响应模型（仅上传和转换）
    """
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="响应消息")
    filename: str = Field(..., description="文件名")
    file_size: str = Field(..., description="文件大小")
    total_pages: int = Field(..., description="总页数")
    image_paths: List[str] = Field(..., description="转换后的图像路径列表")
    temp_dir: str = Field(..., description="临时目录路径")

class AnalyzeRequest(BaseModel):
    """
    图像分析请求模型
    更新原因：将原UploadRequest中的分析相关字段移到这里
    """
    task_id: str = Field(..., description="任务ID")
    provider: LLMProvider = Field(..., description="大模型提供商")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    image_paths: Optional[List[str]] = Field(None, description="指定要分析的图像路径（可选）")
    extract_answers: bool = Field(True, description="是否提取答案")
    extract_knowledge_points: bool = Field(True, description="是否提取考点")
    output_format: str = Field("json", description="输出格式 (json/excel/markdown)")

class AnalyzeResponse(BaseModel):
    """
    图像分析响应模型
    """
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="响应消息")
    total_images: int = Field(..., description="总图像数")
    processed_images: int = Field(..., description="已处理图像数")
    questions: List[Question] = Field(..., description="识别出的题目列表")
    statistics: Dict[str, Any] = Field(..., description="统计信息")
    success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")

class StatusResponse(BaseModel):
    """
    状态查询响应模型
    """
    task_info: TaskInfo = Field(..., description="任务信息")
    message: str = Field(..., description="响应消息")

class ErrorResponse(BaseModel):
    """
    错误响应模型
    """
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细信息")
    task_id: Optional[str] = Field(None, description="任务ID")

class HealthResponse(BaseModel):
    """
    健康检查响应模型
    """
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="版本号")
    timestamp: datetime = Field(..., description="检查时间")
    uptime: str = Field(..., description="运行时间")

# 创建分析任务请求
class CreateAnalysisTaskRequest(BaseModel):
    """创建分析任务请求模型"""
    name: str = Field(..., description="分析任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    image_paths: List[str] = Field(..., description="要分析的图片路径列表")
    provider: LLMProvider = Field(..., description="大模型提供商")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    extract_answers: bool = Field(True, description="是否提取答案")
    extract_knowledge_points: bool = Field(True, description="是否提取考点")
    output_format: str = Field("json", description="输出格式")
    source_upload_task_id: Optional[str] = Field(None, description="来源上传任务ID（可选）")

# 从上传任务创建分析任务请求
class CreateAnalysisFromUploadRequest(BaseModel):
    """从上传任务创建分析任务请求模型"""
    name: str = Field(..., description="分析任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    source_upload_task_id: str = Field(..., description="来源上传任务ID")  # 改名保持一致
    selected_image_indices: Optional[List[int]] = Field(None, description="选择的图片索引（从0开始，None表示全部）")
    provider: LLMProvider = Field(..., description="大模型提供商")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    extract_answers: bool = Field(True, description="是否提取答案")
    extract_knowledge_points: bool = Field(True, description="是否提取考点")
    output_format: str = Field("json", description="输出格式")

# 分析任务创建响应
class CreateAnalysisTaskResponse(BaseModel):
    """创建分析任务响应模型"""
    task_id: str = Field(..., description="分析任务ID")
    name: str = Field(..., description="任务名称")
    message: str = Field(..., description="响应消息")
    total_images: int = Field(..., description="要分析的图片总数")
    estimated_duration: Optional[str] = Field(None, description="预估处理时间")

# 分析任务执行请求
class ExecuteAnalysisTaskRequest(BaseModel):
    """执行分析任务请求模型"""
    task_id: str = Field(..., description="分析任务ID")

# 分析结果响应
class AnalysisResultResponse(BaseModel):
    """分析结果响应模型"""
    task_id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    status: TaskStatus = Field(..., description="任务状态")
    total_images: int = Field(..., description="总图片数")
    processed_images: int = Field(..., description="已处理图片数")
    questions: List[Question] = Field(..., description="识别出的题目列表")
    statistics: Dict[str, Any] = Field(..., description="统计信息")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")

# 上传任务图片列表响应
class UploadTaskImagesResponse(BaseModel):
    """上传任务图片列表响应模型"""
    task_id: str = Field(..., description="上传任务ID")
    filename: str = Field(..., description="PDF文件名")
    total_pages: int = Field(..., description="总页数")
    images: List[Dict[str, Any]] = Field(..., description="图片信息列表")
    # images格式: [{"index": 0, "path": "/path/to/image.png", "page_number": 1, "size": 1024}]