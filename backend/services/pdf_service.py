from pathlib import Path
from typing import List, Tuple, Dict, Any
import uuid
from pdf2image import convert_from_path
from PIL import Image
import logging

from backend.config.settings import settings

logger = logging.getLogger(__name__)

class PDFService:
    """
    PDF处理服务类
    负责PDF文件的上传、转换和页面提取
    """
    
    def __init__(self):
        """
        初始化PDF服务
        """
        self.upload_dir = settings.upload_path
        self.output_dir = settings.output_path
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> Tuple[str, str]:
        """
        保存上传的PDF文件
        
        Args:
            file_content: 文件内容（字节）
            filename: 原始文件名
            
        Returns:
            Tuple[str, str]: (任务ID, 保存的文件路径)
        """
        # 生成唯一的任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务专用目录
        task_dir = self.upload_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        file_path = task_dir / filename
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"文件已保存: {file_path}, 任务ID: {task_id}")
        return task_id, str(file_path)
    
    def validate_file(self, file_path: str, filename: str) -> bool:
        """
        验证上传的文件
        
        Args:
            file_path: 文件路径
            filename: 文件名
            
        Returns:
            bool: 验证是否通过
            
        Raises:
            ValueError: 文件验证失败时抛出异常
        """
        # 读取文件内容进行验证
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
        except Exception as e:
            raise ValueError(f"无法读取文件: {str(e)}")
        
        # 检查文件大小
        if len(file_content) > settings.max_file_size_bytes:
            raise ValueError(f"文件大小超过限制 ({settings.format_file_size(settings.max_file_size_bytes)})")
        
        # 检查文件扩展名
        file_ext = Path(filename).suffix.lower()
        if file_ext not in settings.allowed_extensions:
            raise ValueError(f"不支持的文件格式: {file_ext}")
        
        # 检查文件内容（PDF魔数）
        if not file_content.startswith(b'%PDF'):
            raise ValueError("文件不是有效的PDF格式")
        
        return True
    
    def filter_pages_for_analysis(self, image_paths: List[str], total_pages: int) -> List[str]:
        """
        过滤不需要分析的页面（封面、目录、附录、背面页）
        
        Args:
            image_paths: 所有页面图片路径列表
            total_pages: 总页数
            
        Returns:
            List[str]: 过滤后需要分析的页面路径列表
        """
        if not settings.skip_cover_pages and not settings.skip_toc_pages and \
           not settings.skip_appendix_pages and not settings.skip_back_pages:
            return image_paths
        
        filtered_paths = []
        skip_indices = set()
        
        # 跳过封面页（前几页）
        if settings.skip_cover_pages:
            for i in range(min(settings.max_cover_pages, total_pages)):
                skip_indices.add(i)
                logger.info(f"跳过封面页: 第 {i+1} 页")
        
        # 跳过背面页（后几页）
        if settings.skip_back_pages:
            for i in range(max(0, total_pages - settings.max_back_pages), total_pages):
                skip_indices.add(i)
                logger.info(f"跳过背面页: 第 {i+1} 页")
        
        # 检测并跳过目录页和附录页
        for i, image_path in enumerate(image_paths):
            if i in skip_indices:
                continue
                
            # 通过文件名或页码判断是否为目录页或附录页
            page_num = i + 1
            
            # 简单的启发式规则：目录页通常在前10页内
            if settings.skip_toc_pages and page_num <= 10:
                # 这里可以添加更复杂的目录页检测逻辑
                # 比如OCR识别页面内容是否包含"目录"、"Contents"等关键词
                pass
            
            # 附录页通常在后面
            if settings.skip_appendix_pages and page_num > total_pages * 0.8:
                # 这里可以添加附录页检测逻辑
                # 比如检测是否包含"附录"、"Appendix"等关键词
                pass
            
            filtered_paths.append(image_path)
        
        logger.info(f"页面过滤完成: 总页数 {total_pages}, 跳过 {len(skip_indices)} 页, 待分析 {len(filtered_paths)} 页")
        return filtered_paths
    
    def convert_pdf_to_temp_images(self, pdf_path: str, task_id: str) -> Dict[str, Any]:
        """
        将PDF转换为临时图片（不进行分析）
        
        Args:
            pdf_path: PDF文件路径
            task_id: 任务ID
            
        Returns:
            Dict[str, Any]: 包含成功状态、图片路径列表和临时目录的字典
            
        Raises:
            Exception: PDF转换失败时抛出异常
        """
        try:
            # 创建临时图片目录
            temp_dir = Path(settings.upload_dir) / "temp" / task_id
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 转换PDF为图片
            logger.info(f"开始转换PDF到临时目录: {pdf_path}")
            pages = convert_from_path(
                pdf_path,
                dpi=300,  # 高分辨率
                fmt='PNG'
            )
            
            image_paths = []
            for i, page in enumerate(pages, 1):
                image_path = temp_dir / f"page_{i:03d}.png"
                page.save(image_path, 'PNG')
                image_paths.append(str(image_path))
                logger.debug(f"页面 {i} 已转换到临时目录: {image_path}")
            
            logger.info(f"PDF转换完成，共 {len(image_paths)} 页，临时目录: {temp_dir}")
            return {
                "success": True,
                "image_paths": image_paths,
                "temp_dir": str(temp_dir)  # 改为 temp_dir
            }
            
        except Exception as e:
            logger.error(f"PDF转换失败: {str(e)}")
            return {
                "success": False,
                "error": f"PDF转换失败: {str(e)}",
                "image_paths": [],
                "output_dir": ""
            }
    
    def cleanup_temp_images(self, task_id: str) -> bool:
        """
        清理临时图像文件
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 清理是否成功
        """
        try:
            temp_dir = Path(settings.upload_dir) / "temp" / task_id
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"临时目录已清理: {temp_dir}")
            return True
        except Exception as e:
            logger.error(f"清理临时目录失败: {str(e)}")
            return False
    
    def get_pdf_info(self, pdf_path: str) -> dict:
        """
        获取PDF文件信息
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            dict: PDF信息字典
        """
        try:
            # 先转换一页来获取页数信息
            pages = convert_from_path(pdf_path, first_page=1, last_page=1)
            
            # 获取总页数（这里需要重新转换获取准确页数）
            all_pages = convert_from_path(pdf_path)
            total_pages = len(all_pages)
            
            # 获取文件大小
            file_size = Path(pdf_path).stat().st_size
            
            return {
                "total_pages": total_pages,
                "file_size": file_size,
                "file_size_formatted": settings.format_file_size(file_size)
            }
            
        except Exception as e:
            logger.error(f"获取PDF信息失败: {str(e)}")
            return {
                "total_pages": 0,
                "file_size": 0,
                "file_size_formatted": "未知"
            }
    
    def cleanup_task_files(self, task_id: str) -> bool:
        """
        清理任务相关文件
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 清理是否成功
        """
        try:
            import shutil
            
            # 清理上传目录
            upload_task_dir = self.upload_dir / task_id
            if upload_task_dir.exists():
                shutil.rmtree(upload_task_dir)
            
            # 清理输出目录
            output_task_dir = self.output_dir / task_id
            if output_task_dir.exists():
                shutil.rmtree(output_task_dir)
            
            logger.info(f"任务 {task_id} 的文件已清理")
            return True
            
        except Exception as e:
            logger.error(f"清理任务文件失败: {str(e)}")
            return False