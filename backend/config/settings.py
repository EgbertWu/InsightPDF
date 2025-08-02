from pydantic_settings import BaseSettings
from pydantic import validator
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """
    应用配置管理类
    使用 pydantic 的 BaseSettings 自动从环境变量加载配置
    """
    
    # 应用基础配置
    app_name: str = "InsightPDF API"
    version: str = "v0.1"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    
    # 文件处理配置
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    max_file_size_mb: int = 50  # 文件大小限制（MB）
    allowed_extensions: list = [".pdf"]
    
    # 页面过滤配置
    skip_cover_pages: bool = True  # 跳过封面页
    skip_toc_pages: bool = True    # 跳过目录页
    skip_appendix_pages: bool = True  # 跳过附录页
    skip_back_pages: bool = True   # 跳过背面页
    max_cover_pages: int = 4       # 最多跳过前几页作为封面
    max_back_pages: int = 2        # 最多跳过后几页作为背面
    
    # OpenAI 配置
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    
    # 通义千问配置
    qwen_api_key: Optional[str] = None
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-vl-max"
    
    # API配置
    api_timeout_seconds: int = 300  # API超时时间（秒）
    max_retries: int = 3
    
    class Config:
        """
        Pydantic配置类
        """
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def max_file_size_bytes(self) -> int:
        """
        获取文件大小限制（字节）
        
        Returns:
            int: 文件大小限制，单位为字节
        """
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def api_timeout_ms(self) -> int:
        """
        获取API超时时间（毫秒）
        
        Returns:
            int: API超时时间，单位为毫秒
        """
        return self.api_timeout_seconds * 1000
    
    def __init__(self, **kwargs):
        """
        初始化配置，确保必要的目录存在
        """
        super().__init__(**kwargs)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """
        确保上传和输出目录存在
        """
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def get_llm_config(self, provider: str) -> dict:
        """
        获取指定大模型提供商的配置
        
        Args:
            provider: 提供商名称 ('openai' 或 'qwen')
            
        Returns:
            dict: 包含API密钥、基础URL和模型名称的配置字典
        """
        if provider.lower() == "openai":
            return {
                "api_key": self.openai_api_key,
                "base_url": self.openai_base_url,
                "model": self.openai_model
            }
        elif provider.lower() == "qwen":
            return {
                "api_key": self.qwen_api_key,
                "base_url": self.qwen_base_url,
                "model": self.qwen_model
            }
        else:
            raise ValueError(f"不支持的大模型提供商: {provider}")
    
    @property
    def upload_path(self) -> Path:
        """
        获取上传目录的Path对象
        """
        return Path(self.upload_dir)
    
    @property
    def output_path(self) -> Path:
        """
        获取输出目录的Path对象
        """
        return Path(self.output_dir)
    
    def format_file_size(self, size_bytes: int) -> str:
        """
        格式化文件大小显示
        
        Args:
            size_bytes: 文件大小（字节）
            
        Returns:
            str: 格式化后的文件大小字符串
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

# 创建全局配置实例
settings = Settings()