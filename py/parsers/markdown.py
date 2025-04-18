#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Markdown文档解析器
支持解析常见格式的Markdown API文档
"""

import re
from .base import BaseParser

class MarkdownParser(BaseParser):
    """
    Markdown文档解析器类
    解析常见格式的Markdown API文档
    """
    
    def parse(self, input_path):
        """
        解析Markdown格式的API文档
        
        Args:
            input_path: 文档路径，可以是URL或文件路径
        
        Returns:
            解析后的API数据
        """
        content = self.load_content(input_path)
        
        # 提取API信息
        title = self._extract_title(content)
        description = self._extract_description(content)
        
        api_info = {
            'title': title,
            'description': description,
            'version': self._extract_version(content),
            'endpoints': self._extract_endpoints(content)
        }
        
        return api_info
    
    def _extract_title(self, content):
        """提取API标题"""
        title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        return '未命名API'
    
    def _extract_description(self, content):
        """提取API描述"""
        # 尝试提取标题后的第一段作为描述
        title_match = re.search(r'^#\s+.+?$', content, re.MULTILINE)
        if title_match:
            start_pos = title_match.end()
            next_heading = re.search(r'^#{1,6}\s+', content[start_pos:], re.MULTILINE)
            if next_heading:
                description = content[start_pos:start_pos + next_heading.start()].strip()
            else:
                description = content[start_pos:].strip()
            return description
        return ''
    
    def _extract_version(self, content):
        """提取API版本"""
        version_match = re.search(r'[Vv]ersion[:：]\s*([0-9.]+)', content)
        if version_match:
            return version_match.group(1)
        return '1.0.0'
    
    def _extract_endpoints(self, content):
        """提取API端点信息"""
        endpoints = []
        
        # 查找所有API端点章节（以##或###开头的标题）
        endpoint_sections = re.finditer(r'^(#{2,3})\s+(.+?)$.*?(?=^#{1,3}\s+|\Z)', content, re.MULTILINE | re.DOTALL)
        
        for section in endpoint_sections:
            section_level = len(section.group(1))
            section_title = section.group(2).strip()
            section_content = section.group(0)
            
            # 只处理看起来像API端点的章节
            if section_level == 2 and not self._looks_like_endpoint(section_title):
                continue
            
            # 提取HTTP方法和路径
            method, path = self._extract_method_and_path(section_title, section_content)
            if not method or not path:
                continue
            
            endpoint = {
                'method': method.upper(),
                'path': path,
                'operationId': self._generate_operation_id(method, path),
                'summary': section_title,
                'description': self._extract_endpoint_description(section_content),
                'parameters': self._extract_parameters(section_content),
                'requestBody': self._extract_request_body(section_content),
                'responses': self._extract_responses(section_content)
            }
            
            endpoints.append(endpoint)
        
        return endpoints
    
    def _looks_like_endpoint(self, title):
        """判断标题是否看起来像API端点"""
        methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        for method in methods:
            if method in title.upper():
                return True
        return False
    
    def _extract_method_and_path(self, title, content):
        """提取HTTP方法和路径"""
        # 从标题中提取
        method_path_match = re.search(r'(GET|POST|PUT|DELETE|PATCH)\s+([^\s]+)', title, re.IGNORECASE)
        if method_path_match:
            return method_path_match.group(1), method_path_match.group(2)
        
        # 从内容中提取
        method_path_match = re.search(r'(GET|POST|PUT|DELETE|PATCH)\s+([^\s]+)', content, re.IGNORECASE)
        if method_path_match:
            return method_path_match.group(1), method_path_match.group(2)
        
        # 从代码块中提取
        code_block_match = re.search(r'```[^\n]*\n(GET|POST|PUT|DELETE|PATCH)\s+([^\s\n]+)', content, re.IGNORECASE)
        if code_block_match:
            return code_block_match.group(1), code_block_match.group(2)
        
        return None, None
    
    def _generate_operation_id(self, method, path):
        """生成操作ID"""
        path_part = path.replace('/', '_').strip('_')
        if path_part.startswith('{') and path_part.endswith('}'):
            path_part = 'by_' + path_part[1:-1]
        return f"{method.lower()}_{path_part}"
    
    def _extract_endpoint_description(self, content):
        """提取端点描述"""
        # 提取标题后、参数表格前的内容作为描述
        title_match = re.search(r'^#{2,3}\s+.+?$', content, re.MULTILINE)
        if title_match:
            start_pos = title_match.end()
            # 寻找参数表格或其他章节
            next_section = re.search(r'^#{1,6}\s+|^\|.+\|$', content[start_pos:], re.MULTILINE)
            if next_section:
                description = content[start_pos:start_pos + next_section.start()].strip()
            else:
                description = content[start_pos:].strip()
            return description
        return ''
    
    def _extract_parameters(self, content):
        """提取参数信息"""
        parameters = []
        
        # 查找参数表格
        table_match = re.search(r'^\|(.+?)\|$\n^\|[-:|\s]+\|$\n((?:^\|.+?\|$\n?)+)', content, re.MULTILINE)
        if not table_match:
            return parameters
        
        # 解析表头
        headers = [h.strip() for h in table_match.group(1).split('|')]
        
        # 解析表格行
        rows = table_match.group(2).strip().split('\n')
        for row in rows:
            row_values = [v.strip() for v in row.strip('|').split('|')]
            
            # 创建参数字典
            param = {}
            for i, header in enumerate(headers):
                if i < len(row_values):
                    header_lower = header.lower()
                    if '名称' in header_lower or 'name' in header_lower:
                        param['name'] = row_values[i]
                    elif '类型' in header_lower or 'type' in header_lower:
                        param['schema'] = {'type': row_values[i]}
                    elif '必填' in header_lower or 'required' in header_lower:
                        param['required'] = '是' in row_values[i] or 'yes' in row_values[i].lower() or 'true' in row_values[i].lower()
                    elif '描述' in header_lower or 'description' in header_lower:
                        param['description'] = row_values[i]
                    elif '位置' in header_lower or 'in' in header_lower:
                        in_value = row_values[i].lower()
                        if 'path' in in_value:
                            param['in'] = 'path'
                        elif 'query' in in_value:
                            param['in'] = 'query'
                        elif 'header' in in_value:
                            param['in'] = 'header'
                        elif 'body' in in_value:
                            param['in'] = 'body'
                        elif 'form' in in_value:
                            param['in'] = 'formData'
                        else:
                            param['in'] = 'query'  # 默认
            
            # 确保必要的字段存在
            if 'name' in param:
                if 'in' not in param:
                    # 根据名称猜测参数位置
                    if '{' in param['name'] and '}' in param['name']:
                        param['in'] = 'path'
                    else:
                        param['in'] = 'query'
                
                if 'schema' not in param:
                    param['schema'] = {'type': 'string'}
                
                if 'required' not in param:
                    param['required'] = param.get('in') == 'path'  # 路径参数默认必需
                
                parameters.append(param)
        
        return parameters
    
    def _extract_request_body(self, content):
        """提取请求体信息"""
        # 查找请求体JSON示例
        request_body_match = re.search(r'(?:请求体|[Rr]equest [Bb]ody)[\s\S]*?```(?:json)?\n([\s\S]*?)```', content)
        if request_body_match:
            request_body = {
                'content_type': 'application/json',
                'schema': {
                    'type': 'object',
                    'example': request_body_match.group(1).strip()
                },
                'required': True
            }
            return request_body
        return None
    
    def _extract_responses(self, content):
        """提取响应信息"""
        responses = []
        
        # 查找成功响应示例
        success_match = re.search(r'(?:响应|[Rr]esponse)[\s\S]*?```(?:json)?\n([\s\S]*?)```', content)
        if success_match:
            success_response = {
                'status_code': '200',
                'description': '成功',
                'content_type': 'application/json',
                'schema': {
                    'type': 'object',
                    'example': success_match.group(1).strip()
                }
            }
            responses.append(success_response)
        
        # 如果没有找到任何响应，添加一个默认响应
        if not responses:
            responses.append({
                'status_code': '200',
                'description': '成功',
                'content_type': 'application/json',
                'schema': {}
            })
        
        return responses 