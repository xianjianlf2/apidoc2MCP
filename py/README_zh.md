# apidoc2MCP

将API文档转换为Model Context Protocol (MCP) 服务

## 简介

apidoc2MCP 是一个工具，可以将各种格式的API文档（如OpenAPI/Swagger、Markdown、HTML等）转换为MCP服务定义。
MCP（Model Context Protocol）是一种协议，用于大型语言模型（LLM）与应用程序之间的通信，使模型能够利用应用程序提供的工具、资源和提示。

## 项目结构

```
py/
├── main.py              # 主程序入口
├── pipeline.py          # 处理流水线
├── requirements.txt     # 依赖项文件
├── parsers/             # 解析器模块
│   ├── __init__.py      # 解析器入口
│   ├── base.py          # 基础解析器类
│   ├── swagger.py       # Swagger 2.0解析器
│   ├── openapi.py       # OpenAPI 3.x解析器
│   ├── markdown.py      # Markdown解析器
│   └── crawler.py       # HTML网页爬虫解析器
├── converters/          # 转换器模块
│   └── __init__.py      # 标准格式转换函数
├── generators/          # 生成器模块
│   ├── __init__.py      # 生成器入口
│   └── mcp_generator.py # MCP服务生成器
└── utils/               # 工具模块
    └── logger.py        # 日志工具
```

## 安装

### 使用pip安装

```bash
pip install -r requirements.txt
```

### 使用uv创建环境并安装依赖（推荐）

[uv](https://github.com/astral-sh/uv) 是一个快速的Python包管理器和环境管理工具。使用uv可以更快地创建虚拟环境并安装依赖：

```bash
# 安装uv（如果尚未安装）
pip install uv

# 创建虚拟环境并安装依赖
uv venv
uv pip install -r requirements.txt

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

## 使用方法

### 命令行使用

```bash
python py/main.py <输入文档路径> [--format <文档格式>] [--output <输出目录>] [--name <服务名称>]
```

参数说明：
- `<输入文档路径>`: 输入的API文档路径，可以是本地文件路径或URL
- `--format`: 输入文档的格式，可选值为 `swagger`, `openapi`, `markdown`, `html`, `auto`，默认为 `auto`（自动检测）
- `--output`: 输出目录，默认为 `./O_MCP_SERVER_LIST`
- `--name`: MCP服务名称，如果指定，将作为服务名并自动添加到输出目录后，例如：`./O_MCP_SERVER_LIST/my_service`

示例：

```bash
# 基本用法
python py/main.py api.json

# 指定文档格式和输出目录
python py/main.py api.json --format openapi --output ./my_output

# 指定服务名称
python py/main.py api.json --name weather_api
# 输出目录将为: ./O_MCP_SERVER_LIST/weather_api

# 解析HTML网页中的API信息
python py/main.py https://example.com/api-docs.html --format html
```

### 处理流程

apidoc2MCP 采用三阶段流水线处理：

1. **解析阶段** - 解析不同格式的API文档：
   - OpenAPI 3.x
   - Swagger 2.0
   - Markdown
   - HTML网页（通过爬虫解析）

2. **转换阶段** - 将解析的数据转换为统一的OpenAPI格式：
   - 标准化各种格式的API数据
   - 检验数据完整性
   - 对解析结果进行缓存，提高重复处理效率

3. **生成阶段** - 根据标准化的数据生成MCP服务：
   - 生成MCP服务定义文件(`mcp-service.json`)
   - 生成可直接运行的Python实现代码(`mcp_server.py`)
   - 生成简易的API文档(`README.md`)

### 输出文件

工具会在输出目录生成以下文件：
- `mcp-service.json`: MCP服务定义文件，符合MCP协议规范
- `mcp_server.py`: 可直接运行的MCP服务Python代码，基于MCP Python SDK
- `README.md`: 简易的API文档

## 启动和使用MCP服务

生成的MCP服务基于[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)实现，有多种方式启动：

### 1. 直接运行Python文件

```bash
python <输出目录>/mcp_server.py
```

### 2. 使用MCP CLI工具运行

```bash
# 开发模式运行
mcp dev <输出目录>/mcp_server.py

# 或者直接运行
mcp run <输出目录>/mcp_server.py
```

### 3. 使用环境变量自定义API基础URL

如果需要连接到特定的API服务器，可以通过环境变量设置基础URL：

```bash
# Windows
set API_BASE_URL=https://your-api-base-url
python <输出目录>/mcp_server.py

# Linux/macOS
API_BASE_URL=https://your-api-base-url python <输出目录>/mcp_server.py
```

### 4. 作为服务部署

对于生产环境，可以将生成的MCP服务作为常驻服务部署：

```bash
# 使用nohup在后台运行
nohup python <输出目录>/mcp_server.py > mcp_service.log 2>&1 &

# 或者使用pm2管理（需要先安装pm2）
pm2 start <输出目录>/mcp_server.py --name "mcp-service" --interpreter python
```

### 服务启动后

MCP服务启动后，可以在支持MCP协议的大型语言模型或工具中使用该服务。服务会根据API的特性自动提供以下MCP功能：

1. **工具(Tools)**：所有API接口默认都会通过工具接口实现，采用异步编程方式与后端API通信
   ```python
   @mcp.tool()
   async def search_users(query: str, limit: int) -> str:
       """搜索用户"""
       async with httpx.AsyncClient() as client:
           response = await client.get(f"{BASE_URL}/users/search", params={"q": query, "limit": limit})
           return response.text
   ```

## 特色功能

### HTML文档爬虫解析

apidoc2MCP 支持从普通HTML网页中提取API信息，即使没有标准的OpenAPI/Swagger文档。爬虫解析器会：

- 自动识别页面中的代码块、表格和特定结构
- 提取可能的API路径、HTTP方法和参数信息
- 支持提取命令行接口信息
- 自适应各种HTML结构的页面

对于非结构化的API文档，可以使用 `--format html` 参数指定使用爬虫解析。

### 自动类型转换

系统会自动将不同格式的API文档转换为标准的OpenAPI 3.0格式：

- 支持从Swagger 2.0升级到OpenAPI 3.0
- 支持从Markdown表格提取API信息
- 支持从HTML页面提取API信息
- 支持缓存转换结果，提高效率

### 性能指标

系统会记录各阶段的处理时间和相关指标：

- 解析阶段耗时
- 转换阶段耗时
- 生成阶段耗时
- 总处理时间
- 成功处理的端点数量

## 故障排除

如果服务生成或启动过程中遇到问题：

1. **检查API文档完整性**：确保文档包含完整的路径、方法和参数定义
2. **查看日志输出**：程序会输出详细的日志，指出哪些端点因信息不完整而未实现
3. **检查生成的README.md**：包含了生成的API信息和未实现端点的原因
4. **验证API基础URL**：确保环境变量`API_BASE_URL`设置正确，或在代码中修改
5. **检查依赖项**：确保所有必要的依赖项都已安装，特别是`beautifulsoup4`和`httpx`

## 示例

输入OpenAPI文档：
```yaml
openapi: 3.0.0
info:
  title: 用户API
  version: 1.0.0
paths:
  /users/{id}:
    get:
      summary: 获取用户信息
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        200:
          description: 成功
```

生成的MCP服务代码：
```python
from mcp.server.fastmcp import FastMCP
import httpx
import json
import os

mcp = FastMCP("用户API", dependencies=["httpx"])

# 配置基础URL，可以通过环境变量覆盖
BASE_URL = os.environ.get('API_BASE_URL', '')

@mcp.tool()
async def get_user(id: int) -> str:
    """获取用户信息"""
    # 构建请求URL
    url = BASE_URL + f"/users/{id}"
    
    # 发送请求获取资源
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

if __name__ == "__main__":
    # 启动MCP服务器
    mcp.run()
```

## 许可证

MIT 