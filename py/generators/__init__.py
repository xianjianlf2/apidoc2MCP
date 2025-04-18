#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP服务生成器模块
基于OpenAPI规范生成MCP服务
"""

import os
import json
from .mcp_generator import MCPGenerator
from utils.logger import get_logger

logger = get_logger()

def generate_mcp_service(api_data, output_dir):
    """
    生成MCP服务
    
    Args:
        api_data: OpenAPI规范的API数据
        output_dir: 输出目录
    
    Returns:
        生成是否成功
    """
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 创建MCP生成器实例
    generator = MCPGenerator(api_data)
    
    # 生成MCP服务定义
    mcp_service = generator.generate()
    
    # 如果没有有效端点，则打印警告
    if not mcp_service["functions"]:
        logger.warning("⚠️ 没有找到任何有效的API端点，无法生成MCP服务")
        return False
    
    # 写入MCP服务定义文件
    service_json_path = os.path.join(output_dir, 'mcp-service.json')
    with open(service_json_path, 'w', encoding='utf-8') as f:
        json.dump(mcp_service, f, ensure_ascii=False, indent=2)
    
    # 生成Python代码实现
    python_code_path = os.path.join(output_dir, 'mcp_server.py')
    python_code_result = generator.generate_python_code(python_code_path)
    
    # 如果Python代码生成失败，提示用户
    if python_code_result is False:
        logger.warning("⚠️ Python代码生成失败，请检查API文档完整性")
    
    # 生成简易文档
    doc_path = os.path.join(output_dir, 'README.md')
    generate_documentation(api_data, generator, doc_path)
    
    # 输出汇总信息
    incomplete_count = len(generator.incomplete_endpoints)
    complete_count = len(mcp_service["functions"])
    
    if complete_count > 0:
        logger.info("✅ MCP服务生成完成")
        logger.info(f"- 成功转换的端点: {complete_count} 个")
        if incomplete_count > 0:
            logger.info(f"- 未实现的端点: {incomplete_count} 个 (详见日志和README文件)")
        
        return True
    else:
        logger.error("❌ MCP服务生成失败：没有生成任何有效的端点")
        return False

def generate_documentation(api_data, generator, output_path):
    """
    生成MCP服务文档
    
    Args:
        api_data: OpenAPI规范的API数据
        generator: MCP生成器实例
        output_path: 输出文件路径
    """
    # 获取API信息
    info = api_data.get('info', {})
    title = info.get('title', '未命名API')
    description = info.get('description', '')
    version = info.get('version', '1.0.0')
    
    # 生成文档标题
    doc = f"# {title}\n\n"
    
    # 添加描述
    if description:
        doc += f"{description}\n\n"
    
    # 添加版本信息
    doc += f"版本: {version}\n\n"
    
    # 添加服务器信息
    servers = api_data.get('servers', [])
    if servers:
        doc += "## 服务器\n\n"
        for server in servers:
            doc += f"- {server.get('url')}: {server.get('description', '')}\n"
        doc += "\n"
    
    # 添加可用功能
    doc += "## 可用功能\n\n"
    
    # 从生成器的endpoints中获取端点信息
    for endpoint in generator.endpoints:
        if not generator._validate_endpoint(endpoint):
            continue
            
        operation_id = endpoint.get('operationId', generator._generate_operation_id(endpoint))
        summary = endpoint.get('summary', '')
        
        doc += f"### {operation_id}\n\n"
        
        if summary:
            doc += f"{summary}\n\n"
            
        if endpoint.get('description'):
            doc += f"{endpoint.get('description')}\n\n"
            
        doc += f"**请求方法:** {endpoint.get('method', '').upper()}\n\n"
        doc += f"**请求路径:** {endpoint.get('path', '')}\n\n"
        
        # 参数表格
        params = endpoint.get('parameters', [])
        if params:
            doc += "**参数:**\n\n"
            doc += "| 名称 | 位置 | 类型 | 必填 | 描述 |\n"
            doc += "|------|------|------|------|------|\n"
            
            for param in params:
                name = param.get('name', '')
                in_type = param.get('in', '')
                param_type = param.get('schema', {}).get('type', 'string')
                required = '是' if param.get('required') else '否'
                description = param.get('description', '')
                
                doc += f"| {name} | {in_type} | {param_type} | {required} | {description} |\n"
                
            doc += "\n"
        
        # 请求体
        request_body = endpoint.get('requestBody')
        if request_body:
            doc += "**请求体:**\n\n"
            doc += f"Content-Type: {request_body.get('content_type', 'application/json')}\n\n"
            
            schema = request_body.get('schema', {})
            if schema:
                doc += "Schema:\n\n```json\n"
                doc += json.dumps(schema, ensure_ascii=False, indent=2)
                doc += "\n```\n\n"
        
        # 响应
        responses = endpoint.get('responses', [])
        if responses:
            doc += "**响应:**\n\n"
            
            for response in responses:
                status_code = response.get('status_code', '')
                description = response.get('description', '')
                
                doc += f"**状态码:** {status_code} - {description}\n\n"
                
                content_type = response.get('content_type', '')
                if content_type:
                    doc += f"Content-Type: {content_type}\n\n"
                    
                schema = response.get('schema', {})
                if schema:
                    doc += "Schema:\n\n```json\n"
                    doc += json.dumps(schema, ensure_ascii=False, indent=2)
                    doc += "\n```\n\n"
        
        doc += "---\n\n"
    
    # 添加未实现端点的说明
    if generator.incomplete_endpoints:
        doc += "## 未实现的端点\n\n"
        doc += "以下端点因信息不完整而未实现:\n\n"
        
        for endpoint in generator.incomplete_endpoints:
            method = endpoint.get('method', '未知')
            path = endpoint.get('path', '未知路径')
            reason = generator._get_incompleteness_reason(endpoint)
            doc += f"- **{method.upper()} {path}**: {reason}\n"
            
        doc += "\n"
    
    # 添加启动说明
    doc += "## 启动和使用\n\n"
    doc += "### 方法1: 直接运行\n\n"
    doc += "```bash\n"
    doc += "python mcp_server.py\n"
    doc += "```\n\n"
    
    doc += "### 方法2: 使用MCP CLI工具\n\n"
    doc += "```bash\n"
    doc += "mcp run mcp_server.py\n"
    doc += "```\n\n"
    
    doc += "### 方法3: 设置API基础URL\n\n"
    doc += "```bash\n"
    doc += "API_BASE_URL=https://api.example.com python mcp_server.py\n"
    doc += "```\n\n"
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(doc) 