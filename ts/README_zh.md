# apidoc2MCP

将 API 文档转换为模型上下文协议 (MCP) 服务

## 简介

apidoc2MCP 是一个工具，可以将各种格式的 API 文档（如 OpenAPI/Swagger、Markdown、HTML 等）转换为 MCP 服务定义。
MCP（模型上下文协议）是一个用于大型语言模型（LLMs）和应用程序之间通信的协议，使模型能够利用应用程序提供的工具、资源和提示。

## 项目结构

```
.
├── src/
│   ├── parsers/            # 解析器实现
│   │   ├── index.ts        # 主要入口
│   │   ├── swagger.ts      # Swagger 解析器
│   │   ├── openapi.ts      # OpenAPI 解析器
│   │   ├── markdown.ts     # Markdown 解析器
│   │   └── crawler.ts      # 通用网页爬虫解析器
│   └── utils/              # 工具函数
└── package.json            # 项目依赖
```

## 安装

```bash
# 安装依赖
npm install
```

## 使用方法

### 命令行使用

```bash
npx ts-node src/index.ts <input_doc_path> [--format <doc_format>] [--output <output_dir>] [--name <service_name>]
```

参数：
- `<input_doc_path>`：输入 API 文档的路径，可以是本地文件路径或 URL
- `--format`：输入文档的格式，选项包括 `swagger`、`openapi`、`markdown`、`html`、`auto`，默认为 `auto`（自动检测）
- `--output`：输出目录，默认为 `./O_MCP_SERVER_LIST`
- `--name`：MCP 服务名称，如果指定，将用作服务名称并自动附加到输出目录中，例如 `./O_MCP_SERVER_LIST/my_service`

示例：

```bash
# 基本用法
npx ts-node src/index.ts api.json

# 指定文档格式和输出目录
npx ts-node src/index.ts api.json --format openapi --output ./my_output

# 指定服务名称
npx ts-node src/index.ts api.json --name weather_api
# 输出目录将为：./O_MCP_SERVER_LIST/weather_api

# 从 HTML 网页解析 API 信息
npx ts-node src/index.ts https://example.com/api-docs.html --format html
```

### 处理流程

apidoc2MCP 实现了三阶段处理流程：

1. **解析阶段** - 解析不同格式的 API 文档：
   - OpenAPI 3.x
   - Swagger 2.0
   - Markdown
   - HTML 网页（通过爬虫解析器）

2. **转换阶段** - 将解析的数据转换为统一的 OpenAPI 格式：
   - 标准化来自各种格式的 API 数据
   - 验证数据完整性
   - 缓存解析结果以提高重复处理效率

3. **生成阶段** - 从标准化数据生成 MCP 服务：
   - 生成 MCP 服务定义文件（`mcp-service.json`）
   - 生成可直接运行的 TypeScript 实现代码（`mcp_server.ts`）
   - 生成简单的 API 文档（`README.md`）

### 输出文件

工具在输出目录中生成以下文件：
- `mcp-service.json`：符合 MCP 协议规范的 MCP 服务定义文件
- `mcp_server.ts`：基于 MCP TypeScript SDK 的可直接运行的 MCP 服务 TypeScript 代码
- `README.md`：简单的 API 文档

## 启动和使用 MCP 服务

生成的 MCP 服务基于 MCP TypeScript SDK 实现，可以通过以下几种方式启动：

### 1. 使用 ts-node 运行

```bash
ts-node <output_dir>/mcp_server.ts
```

### 2. 编译并运行

```bash
# 将 TypeScript 编译为 JavaScript
tsc <output_dir>/mcp_server.ts

# 运行编译后的 JavaScript
node <output_dir>/mcp_server.js
```

### 3. 使用环境变量自定义 API 基础 URL

如果需要连接到特定的 API 服务器，可以通过环境变量设置基础 URL：

```bash
# Windows
set API_BASE_URL=https://your-api-base-url
ts-node <output_dir>/mcp_server.ts

# Linux/macOS
API_BASE_URL=https://your-api-base-url ts-node <output_dir>/mcp_server.ts
```

## 主要特性

### HTML 文档爬虫解析器

apidoc2MCP 支持从普通 HTML 网页中提取 API 信息，即使没有标准的 OpenAPI/Swagger 文档。爬虫解析器将：

- 自动识别页面中的代码块、表格和特定结构
- 提取可能的 API 路径、HTTP 方法和参数信息
- 支持提取命令行界面信息
- 适应各种 HTML 结构的页面

对于非结构化的 API 文档，使用 `--format html` 参数指定使用爬虫解析器。

### 自动类型转换

系统自动将不同格式的 API 文档转换为标准的 OpenAPI 3.0 格式：

- 支持从 Swagger 2.0 升级到 OpenAPI 3.0
- 支持从 Markdown 表格中提取 API 信息
- 支持从 HTML 页面中提取 API 信息
- 支持缓存转换结果以提高效率

### 性能指标

系统记录每个阶段的处理时间和相关指标：

- 解析阶段持续时间
- 转换阶段持续时间
- 生成阶段持续时间
- 总处理时间
- 成功处理的端点数量

## 故障排除

如果在服务生成或启动过程中遇到问题：

1. **检查 API 文档完整性**：确保文档包含完整的路径、方法和参数定义
2. **检查日志输出**：程序输出详细日志，指示哪些端点由于信息不完整而未实现
3. **检查生成的 README.md**：包含有关生成的 API 和未实现端点原因的信息
4. **验证 API 基础 URL**：确保环境变量 `API_BASE_URL` 设置正确，或在代码中修改
5. **检查依赖项**：确保安装了所有必要的依赖项

## 许可证

MIT 