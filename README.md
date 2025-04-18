# apidoc2MCP

用于将接口文档转换为MCP服务，便于在各个AI Coding IDE中接入直接生成接口调用代码。

# 设计思路

## 流程

1. 用户输入接口文档（链接、文件等形式）
2. 基于不同文档形式，统一进行解析生成openapi
3. 基于openapi内容，按MCP协议生成MCP服务

