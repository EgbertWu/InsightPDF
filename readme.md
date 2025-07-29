# 📚 PDF 应用题智能识别与整理系统（后端API v0.1）

> 把整本书里的应用题一次性"挖"出来，自动分类、总结答案、提炼考点，并以 Excel/CSV 表格形式交付。  
> 完全基于云端大模型（通义千问、Ollama、Kimi、OpenAI等）进行图像识别和文本理解——前后端分离架构，提供简洁的RESTful API服务。
---

## 🧩 功能总览（v0.1）
| 功能 | 说明 |
|------|------|
| PDF上传 | 支持单文件上传，自动解析为图像页面 |
| 同步处理 | 串行处理所有页面，实时返回结果 |
| 题目识别 | 支持文字、公式、图形混合题，纯大模型视觉理解+推理 |
| 分类归档 | 按题型、知识点、年级、难度等维度自动打标签 |
| 答案与考点 | 提取/生成参考答案，总结知识考点 |
| 来源标注 | 每题附带 `书名_页码` |
| 结果导出 | 直接返回Excel/CSV文件下载 |

---

## 🏗️ 技术栈（v0.1 精简版）
- **架构**：前后端分离，RESTful API
- **后端框架**：FastAPI + Python 3.10+
- **核心理念**：完全依赖大模型的多模态能力，无需本地OCR
- **依赖**  
  ```text
  fastapi          # Web框架
  uvicorn          # ASGI服务器
  python-multipart # 文件上传支持
  openpyxl         # 写 Excel
  pandas           # 写 CSV  
  pydantic         # 数据结构校验
  tenacity         # 重试装饰器
  requests         # API调用
  pillow           # 图像预处理（仅格式转换）
  pdf2image        # PDF转图像

POST /api/v01/process         # 上传PDF并同步处理，返回结果
GET  /api/v01/models          # 获取可用模型列表
POST /api/v01/config/model    # 切换使用的大模型

## 后续版本规划
- v0.2 ：添加异步任务处理
- v0.3 ：引入Redis缓存和任务队列
- v1.0 ：支持并发处理和批量任务管理

## 文档目录
InsightPDF/
├── readme.md
├── requirements.txt
├── .env.example
├── .gitignore
└── backend/
    ├── __init__.py
    ├── main.py              # FastAPI应用入口
    ├── config/
    │   ├── __init__.py
    │   └── settings.py      # 配置管理
    ├── api/
    │   ├── __init__.py
    │   ├── v01/
    │   │   ├── __init__.py
    │   │   ├── endpoints/
    │   │   │   ├── __init__.py
    │   │   │   ├── process.py    # PDF处理接口
    │   │   │   └── models.py     # 模型管理接口
    │   │   └── router.py         # 路由汇总
    ├── core/
    │   ├── __init__.py
    │   ├── pdf_processor.py     # PDF解析核心
    │   ├── llm_client.py        # 大模型调用客户端
    │   └── question_extractor.py # 题目提取逻辑
    ├── models/
    │   ├── __init__.py
    │   ├── request.py           # 请求数据模型
    │   ├── response.py          # 响应数据模型
    │   └── question.py          # 题目数据模型
    ├── services/
    │   ├── __init__.py
    │   ├── export_service.py    # 导出服务
    │   └── llm_service.py       # 大模型服务
    └── utils/
        ├── __init__.py
        ├── file_utils.py        # 文件处理工具
        └── logger.py            # 日志工具