#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OpenAPI规范解析器
支持解析OpenAPI 3.x规范的API文档
"""

import json
import yaml
from .base import BaseParser

class OpenAPIParser(BaseParser):
    """
    OpenAPI规范解析器类
    解析OpenAPI 3.x规范的API文档
    """
    
    def parse(self, input_path):
        """
        解析OpenAPI规范文档
        
        Args:
            input_path: 文档路径，可以是URL或文件路径
        
        Returns:
            解析后的API数据
        """
        content = self.load_content(input_path)
        
        # 尝试解析为JSON或YAML
        try:
            # 首先尝试解析为JSON
            api_spec = json.loads(content)
        except json.JSONDecodeError:
            # 如果不是JSON，尝试解析为YAML
            try:
                api_spec = yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ValueError(f"无法解析API文档: {str(e)}")
        
        # 验证是否为OpenAPI文档
        if 'openapi' not in api_spec:
            raise ValueError("文档不符合OpenAPI规范")
        
        # 提取API信息
        api_info = {
            'title': api_spec.get('info', {}).get('title', '未命名API'),
            'description': api_spec.get('info', {}).get('description', ''),
            'version': api_spec.get('info', {}).get('version', '1.0.0'),
            'endpoints': []
        }
        
        # 提取API端点信息
        paths = api_spec.get('paths', {})
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    endpoint = {
                        'path': path,
                        'method': method.upper(),
                        'operationId': operation.get('operationId', f"{method}_{path}".replace('/', '_')),
                        'summary': operation.get('summary', ''),
                        'description': operation.get('description', ''),
                        'parameters': [],
                        'requestBody': None,
                        'responses': []
                    }
                    
                    # 提取参数信息
                    for param in operation.get('parameters', []):
                        param_info = {
                            'name': param.get('name', ''),
                            'in': param.get('in', ''),
                            'required': param.get('required', False),
                            'description': param.get('description', ''),
                            'schema': param.get('schema', {})
                        }
                        endpoint['parameters'].append(param_info)
                    
                    # 提取请求体信息
                    if 'requestBody' in operation:
                        request_body = operation['requestBody']
                        content_type = next(iter(request_body.get('content', {})), None)
                        if content_type:
                            endpoint['requestBody'] = {
                                'content_type': content_type,
                                'schema': request_body['content'][content_type].get('schema', {}),
                                'required': request_body.get('required', False)
                            }
                    
                    # 提取响应信息
                    for status_code, response in operation.get('responses', {}).items():
                        content_type = next(iter(response.get('content', {})), None)
                        response_info = {
                            'status_code': status_code,
                            'description': response.get('description', ''),
                            'content_type': content_type,
                            'schema': {}
                        }
                        if content_type:
                            response_info['schema'] = response['content'][content_type].get('schema', {})
                        endpoint['responses'].append(response_info)
                    
                    api_info['endpoints'].append(endpoint)
        
        return api_info 