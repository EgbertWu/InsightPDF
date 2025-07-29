#!/usr/bin/env python3
"""
应用启动脚本
提供开发和生产环境的启动选项
"""

import argparse
import uvicorn
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.config.settings import settings

def main():
    """
    主函数，解析命令行参数并启动应用
    """
    parser = argparse.ArgumentParser(description="InsightPDF API 服务器")
    parser.add_argument(
        "--host",
        default=settings.host,
        help=f"服务器主机地址 (默认: {settings.host})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"服务器端口 (默认: {settings.port})"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.debug,
        help="启用自动重载 (开发模式)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="工作进程数量 (生产模式)"
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="日志级别"
    )
    
    args = parser.parse_args()
    
    print(f"启动 InsightPDF API 服务器...")
    print(f"主机: {args.host}")
    print(f"端口: {args.port}")
    print(f"调试模式: {args.reload}")
    print(f"文档地址: http://{args.host}:{args.port}/docs")
    print("-" * 50)
    
    # 启动服务器
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=args.log_level
    )

if __name__ == "__main__":
    main()