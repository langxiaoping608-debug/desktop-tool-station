# 桌面工具站

一个使用 Python 内置 HTTP 服务运行的本地工具站，包含派工查询、工单备注替换、公交综合查询和 AI 话术组织功能。

## 本地运行

1. 安装 Python 3.10 或更高版本。
2. 安装依赖：`pip install -r requirements.txt`
3. 如需使用 AI 功能，设置环境变量 `DEEPSEEK_API_KEY`。
4. 运行：`python 桌面工具站.py`
5. 浏览器访问：`http://localhost:8888`

可使用 `PORT` 修改端口，使用 `DESKTOP_TOOL_DIR` 指定网页文件目录。

## 部署说明

本项目含 Python 后端与 API 请求，不能直接运行在 GitHub Pages。GitHub 仓库用于版本管理；若需要公网在线访问，应部署到支持 Python 常驻服务的平台，并在平台中安全配置 `DEEPSEEK_API_KEY`。

仓库包含 `render.yaml`，可通过 Render Blueprint 直接创建 Web Service。

## 安全

请勿把 DeepSeek API 密钥提交到仓库。项目已忽略 `.env` 文件。
