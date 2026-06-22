# apidoc2MCP

> Convert API documentation into **MCP** services — so AI Coding IDEs (Cursor, Claude, etc.) can call your APIs directly.

[English](#english) · [中文](#中文)

## English

`apidoc2MCP` parses API documentation in multiple formats and generates a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) service definition, so LLM-powered tools can discover and invoke your endpoints as tools.

### Supported input formats

- **OpenAPI 3.x** (`.json` / `.yaml`)
- **Swagger 2.0**
- **Markdown** API docs
- **HTML** pages (via a generic crawler)

### How it works

```
API docs (link / file)  ─▶  Parse  ─▶  Unified OpenAPI  ─▶  Generate MCP service
   OpenAPI / Swagger          parsers/                          generators/
   Markdown / HTML
```

### Two implementations

| Dir | Status | Notes |
|-----|--------|-------|
| [`py/`](./py) | ✅ Full pipeline | Parsers + converter + **MCP generator** + CLI entry (`main.py`). Recommended. |
| [`ts/`](./ts) | 🧪 Parser playground | TypeScript parsers + debug examples for the same formats. |

### Quick start (Python)

```bash
cd py

# with uv (recommended)
uv venv && uv pip install -r requirements.txt
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# or with pip
pip install -r requirements.txt

python main.py                     # see py/README.md for full options
```

See **[`py/README.md`](./py/README.md)** for full usage, and **[`ts/README.md`](./ts/README.md)** for the TypeScript parser/debug guide.

---

## 中文

`apidoc2MCP` 将多种格式的接口文档解析后，按 [MCP 协议](https://modelcontextprotocol.io/) 生成 MCP 服务定义，让 AI Coding IDE（Cursor、Claude 等）能把你的接口当作工具直接调用。

### 支持的输入格式

- **OpenAPI 3.x**（`.json` / `.yaml`）
- **Swagger 2.0**
- **Markdown** 接口文档
- **HTML** 页面（通用爬虫解析）

### 处理流程

```
接口文档（链接/文件）─▶ 解析 ─▶ 统一 OpenAPI ─▶ 生成 MCP 服务
```

### 两套实现

| 目录 | 状态 | 说明 |
|------|------|------|
| [`py/`](./py) | ✅ 完整流程 | 解析器 + 转换 + **MCP 生成器** + CLI 入口（`main.py`），推荐使用 |
| [`ts/`](./ts) | 🧪 解析器 | TypeScript 版解析器与调试示例 |

快速开始见 **[`py/README.md`](./py/README.md)**。
