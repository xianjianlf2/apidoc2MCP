#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP服务生成器
基于OpenAPI规范数据生成MCP服务
"""

import re
import httpx
from utils.logger import get_logger

logger = get_logger()


class MCPGenerator:
    """
    MCP服务生成器类
    从OpenAPI规范生成MCP服务
    """

    def __init__(self, api_data):
        """
        初始化MCP生成器

        Args:
            api_data: OpenAPI规范的API数据
        """
        self.api_data = api_data
        self.incomplete_endpoints = []
        # 将OpenAPI规范转换为标准中间格式
        self.endpoints = self._extract_endpoints_from_openapi()

    def _extract_endpoints_from_openapi(self):
        """
        从OpenAPI规范中提取端点信息

        Returns:
            端点列表
        """
        endpoints = []
        
        # 检查是否已经是我们的中间格式（有endpoints字段）
        if 'endpoints' in self.api_data and isinstance(self.api_data['endpoints'], list):
            return self.api_data['endpoints']
            
        # 如果是OpenAPI规范，则从paths中提取端点
        paths = self.api_data.get('paths', {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                    # 创建端点对象
                    endpoint = {
                        'path': path,
                        'method': method,
                        'operationId': operation.get('operationId', ''),
                        'summary': operation.get('summary', ''),
                        'description': operation.get('description', ''),
                        'parameters': []
                    }
                    
                    # 处理参数
                    for param in operation.get('parameters', []):
                        endpoint['parameters'].append({
                            'name': param.get('name', ''),
                            'in': param.get('in', ''),
                            'description': param.get('description', ''),
                            'required': param.get('required', False),
                            'schema': param.get('schema', {'type': 'string'})
                        })
                    
                    # 处理请求体
                    if 'requestBody' in operation:
                        content = operation['requestBody'].get('content', {})
                        content_type = next(iter(content.keys()), 'application/json')
                        schema = content.get(content_type, {}).get('schema', {})
                        
                        endpoint['requestBody'] = {
                            'content_type': content_type,
                            'required': operation['requestBody'].get('required', False),
                            'schema': schema
                        }
                        
                        # 如果请求体是对象类型，从schema中提取属性作为参数
                        if schema.get('type') == 'object' and 'properties' in schema:
                            required_props = schema.get('required', [])
                            for prop_name, prop_schema in schema['properties'].items():
                                endpoint['parameters'].append({
                                    'name': prop_name,
                                    'in': 'body',
                                    'description': prop_schema.get('description', ''),
                                    'required': prop_name in required_props,
                                    'schema': prop_schema
                                })
                    
                    # 处理响应
                    responses = []
                    for status_code, response in operation.get('responses', {}).items():
                        content = response.get('content', {})
                        content_type = next(iter(content.keys()), '')
                        schema = content.get(content_type, {}).get('schema', {})
                        
                        responses.append({
                            'status_code': status_code,
                            'description': response.get('description', ''),
                            'content_type': content_type,
                            'schema': schema
                        })
                    
                    endpoint['responses'] = responses
                    endpoints.append(endpoint)
        
        logger.info(f"🔍 从OpenAPI规范中提取了 {len(endpoints)} 个端点")
        return endpoints

    def generate(self):
        """
        生成MCP服务定义

        Returns:
            MCP服务定义对象
        """
        mcp_service = {
            "functions": []
        }

        for endpoint in self.endpoints:
            # 验证端点信息完整性
            if self._validate_endpoint(endpoint):
                function = self._create_function(endpoint)
                mcp_service["functions"].append(function)
            else:
                logger.warning(
                    f"⚠️ 跳过不完整的端点: {endpoint.get('path', '未知路径')} [{endpoint.get('method', '未知方法')}]")
                self.incomplete_endpoints.append(endpoint)

        return mcp_service

    def generate_python_code(self, output_path):
        """
        生成Python代码的MCP服务

        Args:
            output_path: 输出文件路径
            
        Returns:
            布尔值，生成是否成功
        """
        # 生成导入语句
        code = "#!/usr/bin/env python\n"
        code += "# -*- coding: utf-8 -*-\n\n"
        code += "from mcp.server.fastmcp import FastMCP\n"
        code += "import json\n"
        code += "import requests\n"
        code += "import os\n"
        code += "import httpx\n"
        code += "from typing import Dict, List, Any, Optional, Union\n\n"

        # 创建MCP服务实例
        app_name = self.api_data.get('info', {}).get('title', 'API Service')
        version = self.api_data.get('info', {}).get('version', '1.0.0')
        description = self.api_data.get('info', {}).get('description', '')
        
        code += f"# {app_name} v{version}\n"
        if description:
            code += f"# {description}\n"
        code += f"mcp = FastMCP(\"{app_name}\", dependencies=[\"httpx\"])\n\n"

        # 添加基础URL配置
        code += "# 配置基础URL，可以通过环境变量覆盖\n"
        code += "BASE_URL = os.environ.get('API_BASE_URL', '')\n\n"

        # 添加通用的请求函数
        code += "def make_request(method, url, headers=None, params=None, data=None, json_data=None):\n"
        code += "    \"\"\"\n"
        code += "    发送HTTP请求并处理响应\n"
        code += "    \"\"\"\n"
        code += "    try:\n"
        code += "        response = requests.request(\n"
        code += "            method=method,\n"
        code += "            url=url,\n"
        code += "            headers=headers,\n"
        code += "            params=params,\n"
        code += "            data=data,\n"
        code += "            json=json_data\n"
        code += "        )\n"
        code += "        response.raise_for_status()\n"
        code += "        \n"
        code += "        # 尝试解析JSON响应\n"
        code += "        try:\n"
        code += "            return json.dumps(response.json(), ensure_ascii=False)\n"
        code += "        except ValueError:\n"
        code += "            return response.text\n"
        code += "    except requests.exceptions.RequestException as e:\n"
        code += "        return json.dumps({'error': str(e)}, ensure_ascii=False)\n\n"

        # 生成各个端点的完整实现
        valid_endpoints_count = 0
        for endpoint in self.endpoints:
            # 验证端点信息完整性
            if not self._validate_endpoint(endpoint):
                continue

            valid_endpoints_count += 1
            # 获取操作ID和路径
            operation_id = endpoint.get('operationId', '')
            if not operation_id:
                operation_id = self._generate_operation_id(endpoint)

            path = endpoint.get('path', '')
            method = endpoint.get('method', '').upper()
            description = endpoint.get('summary', '')
            if endpoint.get('description'):
                description = f"{description}\n{endpoint.get('description')}"

            # 统一生成工具接口
            code += self._generate_tool_code(endpoint, operation_id, path)

            code += "\n\n"

        # 如果没有有效端点，打印警告
        if valid_endpoints_count == 0:
            logger.warning("⚠️ 没有发现有效的API端点，无法生成MCP服务代码")
            return None

        # 如果有不完整的端点，添加注释说明
        if self.incomplete_endpoints:
            code += "# 以下端点因信息不完整而未实现:\n"
            for endpoint in self.incomplete_endpoints:
                method = endpoint.get('method', '未知')
                path = endpoint.get('path', '未知路径')
                reason = self._get_incompleteness_reason(endpoint)
                code += f"# {method} {path}: {reason}\n"
            code += "\n"

        # 添加启动代码
        code += "if __name__ == \"__main__\":\n"
        code += "    # 启动MCP服务器\n"
        code += "    mcp.run()\n"

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(code)

        # 如果有不完整的端点，打印汇总信息
        if self.incomplete_endpoints:
            logger.warning(
                f"⚠️ 共有 {len(self.incomplete_endpoints)} 个端点因信息不完整而未实现")
            for endpoint in self.incomplete_endpoints:
                method = endpoint.get('method', '未知')
                path = endpoint.get('path', '未知路径')
                reason = self._get_incompleteness_reason(endpoint)
                logger.warning(f"  - {method} {path}: {reason}")
                
        # 返回生成状态
        if valid_endpoints_count > 0:
            logger.info(f"✅ 成功生成 {valid_endpoints_count} 个API端点的MCP接口")
            return True
        else:
            return False

    def _validate_endpoint(self, endpoint):
        """
        验证端点信息是否完整

        Args:
            endpoint: API端点数据

        Returns:
            布尔值，端点信息是否完整
        """
        # 检查基本信息
        if not endpoint.get('path'):
            return False

        if not endpoint.get('method'):
            return False

        # 对于路径参数，检查是否在parameters中定义
        path_params = re.findall(r'{([^}]+)}', endpoint.get('path', ''))
        defined_path_params = [p.get('name') for p in endpoint.get(
            'parameters', []) if p.get('in') == 'path']

        for param in path_params:
            if param not in defined_path_params:
                return False

        return True

    def _get_incompleteness_reason(self, endpoint):
        """
        获取端点信息不完整的原因

        Args:
            endpoint: API端点数据

        Returns:
            不完整的原因描述
        """
        if not endpoint.get('path'):
            return "缺少API路径"

        if not endpoint.get('method'):
            return "缺少HTTP方法"

        # 检查路径参数
        path_params = re.findall(r'{([^}]+)}', endpoint.get('path', ''))
        defined_path_params = [p.get('name') for p in endpoint.get(
            'parameters', []) if p.get('in') == 'path']

        missing_params = [
            param for param in path_params if param not in defined_path_params]
        if missing_params:
            return f"路径参数未定义: {', '.join(missing_params)}"

        return "未知原因"

    def _is_resource_endpoint(self, endpoint):
        """
        判断端点是否为资源型接口

        Args:
            endpoint: API端点数据

        Returns:
            布尔值，是否为资源型接口
        """
        # 通常GET方法用于获取资源
        if endpoint.get('method', '').upper() == 'GET':
            return True
        return False

    def _convert_path_to_resource(self, path):
        """
        将API路径转换为MCP资源路径
        
        Args:
            path: API路径
        
        Returns:
            MCP资源路径
        """
        # 将 /api/users/{id} 格式转换为 api://users/{id} 格式
        path = path.lstrip('/')
        
        # 提取路径参数，确保函数参数与URL参数一致
        path_params = re.findall(r'{([^}]+)}', path)
        
        # 如果路径以API开头，则创建对应的资源类型
        if path.startswith('api/'):
            path = path.replace('api/', '', 1)
            
        # 生成资源路径
        resource_path = path + "://"
        
        return resource_path
    
    def _generate_resource_code(self, endpoint, operation_id, path):
        """
        生成资源接口代码
        
        Args:
            endpoint: API端点数据
            operation_id: 操作ID
            path: 接口路径
        
        Returns:
            资源接口代码字符串
        """
        # 替换路径中的参数为MCP资源模式
        resource_path = self._convert_path_to_resource(path)
        
        # 获取参数
        parameters = self._create_parameters(endpoint)
        
        # 提取路径参数名称，用于确保函数参数与URI参数一致
        path_params = re.findall(r'{([^}]+)}', path)
        
        # 构建函数定义
        code = f'@mcp.resource("{resource_path}")\n'
        code += f"def {operation_id}("
        
        # 添加函数参数
        param_list = []
        
        # 确保函数参数包含所有路径参数
        for param_name in path_params:
            # 查找对应的参数定义
            param_def = next((p for p in parameters if p.get('name') == param_name), None)
            if param_def:
                param_type = self._get_python_type(
                    param_def.get('schema', {}).get('type', 'string'))
            else:
                # 如果在parameters中找不到，创建一个默认的字符串参数
                param_type = 'str'
                parameters.append({
                    'name': param_name,
                    'in': 'path',
                    'required': True,
                    'schema': {'type': 'string'}
                })
                logger.warning(f"在参数定义中找不到路径参数 {param_name}，已添加默认字符串参数")
            
            param_list.append(f"{param_name}: {param_type}")
        
        # 添加其他非路径参数
        for param in parameters:
            param_name = param.get('name')
            # 如果不是路径参数，或者是路径参数但尚未添加到列表中
            if param.get('in') != 'path' or param_name not in path_params:
                param_type = self._get_python_type(
                    param.get('schema', {}).get('type', 'string'))
                param_list.append(f"{param_name}: {param_type}")
        
        code += ", ".join(param_list)
        code += ") -> str:\n"
        
        # 添加文档字符串
        description = endpoint.get('summary', '')
        if endpoint.get('description'):
            description = f"{description}\n{endpoint.get('description')}"
        
        code += f'    """{description}"""\n'
        
        # 构建实际请求实现
        api_path = path
        method = endpoint.get('method', '').upper()
        
        # 替换路径参数
        code += "    # 构建请求URL\n"
        code += "    url = BASE_URL + f\"" + \
            self._replace_path_params(api_path) + "\"\n"
        
        # 处理查询参数
        query_params = [p for p in parameters if p.get('in') == 'query']
        if query_params:
            code += "    \n"
            code += "    # 添加查询参数\n"
            code += "    params = {}\n"
            for param in query_params:
                param_name = param.get('name')
                code += f"    if {param_name} is not None:\n"
                code += f"        params['{param_name}'] = {param_name}\n"
        else:
            code += "    params = None\n"
        
        # 处理请求头
        header_params = [p for p in parameters if p.get('in') == 'header']
        if header_params:
            code += "    \n"
            code += "    # 添加请求头\n"
            code += "    headers = {}\n"
            for param in header_params:
                param_name = param.get('name')
                code += f"    if {param_name} is not None:\n"
                code += f"        headers['{param_name}'] = {param_name}\n"
        else:
            code += "    headers = None\n"
        
        # 发送请求
        code += "    \n"
        code += "    # 发送请求获取资源\n"
        code += f"    return make_request('{method}', url, headers=headers, params=params)\n"
        
        return code

    def _generate_tool_code(self, endpoint, operation_id, path):
        """
        生成工具接口代码

        Args:
            endpoint: API端点数据
            operation_id: 操作ID
            path: 接口路径

        Returns:
            工具接口代码字符串
        """
        # 获取参数
        parameters = self._create_parameters(endpoint)

        # 构建函数定义
        code = f'@mcp.tool()\n'
        code += f"async def {operation_id}("

        # 添加函数参数
        param_list = []
        for param in parameters:
            param_name = param.get('name')
            param_type = self._get_python_type(
                param.get('schema', {}).get('type', 'string'))
            param_list.append(f"{param_name}: {param_type}")

        code += ", ".join(param_list)
        code += ") -> str:\n"

        # 添加文档字符串
        description = endpoint.get('summary', '')
        if endpoint.get('description'):
            description = f"{description}\n{endpoint.get('description')}"

        code += f'    """{description}"""\n'

        # 构建实际请求实现
        api_path = path
        method = endpoint.get('method', '').upper()

        # 替换路径参数
        code += "    # 构建请求URL\n"
        code += "    url = BASE_URL + f\"" + \
            self._replace_path_params(api_path) + "\"\n"

        # 处理查询参数
        query_params = [p for p in parameters if p.get('in') == 'query']
        if query_params:
            code += "    \n"
            code += "    # 添加查询参数\n"
            code += "    params = {}\n"
            for param in query_params:
                param_name = param.get('name')
                code += f"    if {param_name} is not None:\n"
                code += f"        params['{param_name}'] = {param_name}\n"
        else:
            code += "    params = None\n"

        # 处理请求头
        header_params = [p for p in parameters if p.get('in') == 'header']
        if header_params:
            code += "    \n"
            code += "    # 添加请求头\n"
            code += "    headers = {}\n"
            for param in header_params:
                param_name = param.get('name')
                code += f"    if {param_name} is not None:\n"
                code += f"        headers['{param_name}'] = {param_name}\n"
        else:
            code += "    headers = None\n"

        # 处理请求体
        body_params = [p for p in parameters if p.get('in') == 'body']
        request_body = endpoint.get('requestBody')

        if request_body:
            content_type = request_body.get('content_type', '')
            if 'application/json' in content_type:
                code += "    \n"
                code += "    # 添加JSON请求体\n"
                code += "    json_data = {}\n"
                for param in body_params:
                    param_name = param.get('name')
                    code += f"    if {param_name} is not None:\n"
                    code += f"        json_data['{param_name}'] = {param_name}\n"
                code += "    data = None\n"
            else:
                code += "    \n"
                code += "    # 添加表单请求体\n"
                code += "    data = {}\n"
                for param in body_params:
                    param_name = param.get('name')
                    code += f"    if {param_name} is not None:\n"
                    code += f"        data['{param_name}'] = {param_name}\n"
                code += "    json_data = None\n"
        else:
            code += "    data = None\n"
            code += "    json_data = None\n"

        # 发送请求
        code += "    \n"
        code += "    # 发送请求执行操作\n"
        code += "    async with httpx.AsyncClient() as client:\n"
        code += f"        response = await client.request('{method}', url, headers=headers, params=params, data=data, json=json_data)\n"
        code += "        return response.text\n"

        return code

    def _replace_path_params(self, path):
        """
        替换路径中的参数为Python f-string格式

        Args:
            path: API路径

        Returns:
            替换后的路径字符串
        """
        return re.sub(r'{([^}]+)}', r'{\1}', path)

    def _get_python_type(self, api_type):
        """
        将API类型转换为Python类型提示

        Args:
            api_type: API类型字符串

        Returns:
            Python类型字符串
        """
        type_map = {
            'integer': 'int',
            'number': 'float',
            'string': 'str',
            'boolean': 'bool',
            'array': 'list',
            'object': 'dict',
            'file': 'str',
            'binary': 'bytes'
        }

        return type_map.get(api_type.lower(), 'str')

    def _create_function(self, endpoint):
        """
        创建MCP函数定义

        Args:
            endpoint: API端点数据

        Returns:
            MCP函数定义对象
        """
        # 构建函数名
        operation_id = endpoint.get('operationId', '')
        if not operation_id:
            operation_id = self._generate_operation_id(endpoint)

        # 构建函数描述
        description = endpoint.get('summary', '')
        if endpoint.get('description'):
            description = f"{description}\n{endpoint.get('description')}"

        # 构建函数参数
        parameters = self._create_parameters(endpoint)

        # 构建MCP函数定义
        function = {
            "name": operation_id,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

        # 添加参数属性
        for param in parameters:
            param_name = param.get('name')
            function["parameters"]["properties"][param_name] = {
                "type": self._get_json_schema_type(param.get('schema', {}).get('type', 'string')),
                "description": param.get('description', '')
            }

            # 如果参数是必需的，添加到required列表
            if param.get('required'):
                function["parameters"]["required"].append(param_name)

        return function

    def _generate_operation_id(self, endpoint):
        """
        生成操作ID

        Args:
            endpoint: API端点数据

        Returns:
            操作ID字符串
        """
        method = endpoint.get('method', '').lower()
        path = endpoint.get('path', '')

        # 移除路径中的特殊字符
        path = re.sub(r'[{}\/]', '_', path).strip('_')

        return f"{method}_{path}"

    def _create_parameters(self, endpoint):
        """
        创建MCP函数参数

        Args:
            endpoint: API端点数据

        Returns:
            参数列表
        """
        parameters = []

        # 添加路径、查询和头部参数
        for param in endpoint.get('parameters', []):
            if param.get('in') in ['path', 'query', 'header']:
                parameters.append(param)

        # 添加请求体参数
        request_body = endpoint.get('requestBody')
        if request_body:
            # 如果请求体是JSON对象，添加其属性作为参数
            content_type = request_body.get('content_type', '')
            schema = request_body.get('schema', {})

            if 'application/json' in content_type and schema.get('type') == 'object':
                properties = schema.get('properties', {})
                required_props = schema.get('required', [])

                for prop_name, prop_schema in properties.items():
                    param = {
                        'name': prop_name,
                        'in': 'body',
                        'description': prop_schema.get('description', ''),
                        'required': prop_name in required_props,
                        'schema': prop_schema
                    }
                    parameters.append(param)
            else:
                # 如果不是JSON对象，添加一个整体的body参数
                param = {
                    'name': 'body',
                    'in': 'body',
                    'description': '请求体数据',
                    'required': request_body.get('required', False),
                    'schema': schema
                }
                parameters.append(param)

        return parameters

    def _get_json_schema_type(self, api_type):
        """
        将API类型转换为JSON Schema类型

        Args:
            api_type: API类型字符串

        Returns:
            JSON Schema类型字符串
        """
        type_map = {
            'integer': 'integer',
            'number': 'number',
            'string': 'string',
            'boolean': 'boolean',
            'array': 'array',
            'object': 'object',
            'file': 'string',
            'binary': 'string'
        }

        return type_map.get(api_type.lower(), 'string')

    def generate_documentation(self, output_path):
        """
        生成MCP服务文档

        Args:
            output_path: 输出文件路径
        """
        doc = f"# {self.api_data.get('title', '未命名API')}\n\n"

        if self.api_data.get('description'):
            doc += f"{self.api_data.get('description')}\n\n"

        doc += f"版本: {self.api_data.get('version', '1.0.0')}\n\n"

        doc += "## 可用功能\n\n"

        for endpoint in self.api_data.get('endpoints', []):
            if not self._validate_endpoint(endpoint):
                continue

            operation_id = endpoint.get(
                'operationId', self._generate_operation_id(endpoint))
            summary = endpoint.get('summary', '')

            doc += f"### {operation_id}\n\n"

            if summary:
                doc += f"{summary}\n\n"

            if endpoint.get('description'):
                doc += f"{endpoint.get('description')}\n\n"

            doc += f"**请求方法:** {endpoint.get('method', '')}\n\n"
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
                if 'example' in schema:
                    doc += "示例:\n\n```json\n"
                    doc += f"{schema['example']}\n"
                    doc += "```\n\n"

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
                    if 'example' in schema:
                        doc += "示例:\n\n```json\n"
                        doc += f"{schema['example']}\n"
                        doc += "```\n\n"

            doc += "---\n\n"

        # 添加不完整端点的说明
        if self.incomplete_endpoints:
            doc += "## 未实现的端点\n\n"
            doc += "以下端点因信息不完整而未实现:\n\n"

            for endpoint in self.incomplete_endpoints:
                method = endpoint.get('method', '未知')
                path = endpoint.get('path', '未知路径')
                reason = self._get_incompleteness_reason(endpoint)
                doc += f"- **{method} {path}**: {reason}\n"

            doc += "\n"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(doc)
