from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    """
    任务状态枚举
    """
    PENDING = "pending"      # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败

class LLMProvider(str, Enum):
    """
    大模型提供商枚举
    """
    OPENAI = "openai"
    QWEN = "qwen"

class DifficultyLevel(str, Enum):
    """
    难度等级枚举
    """
    EASY = "easy"        # 简单
    MEDIUM = "medium"    # 中等
    HARD = "hard"        # 困难

# 请求模型
class UploadRequest(BaseModel):
    """
    文件上传请求模型
    """
    llm_provider: LLMProvider = Field(..., description="大模型提供商")
    extract_answers: bool = Field(True, description="是否提取答案")
    extract_knowledge_points: bool = Field(True, description="是否提取考点")
    output_format: str = Field("json", description="输出格式 (json/excel/markdown)")

class ProcessRequest(BaseModel):
    """
    处理请求模型
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

class UploadResponse(BaseModel):
    """
    上传响应模型
    """
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="响应消息")
    filename: str = Field(..., description="文件名")
    file_size: str = Field(..., description="文件大小")

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