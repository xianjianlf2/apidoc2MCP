#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Swagger规范解析器
支持解析Swagger 2.0规范的API文档
"""

import json
import yaml
from .base import BaseParser

class SwaggerParser(BaseParser):
    """
    Swagger规范解析器类
    解析Swagger 2.0规范的API文档
    """
    
    def parse(self, input_path):
        """
        解析Swagger规范文档
        
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
        
        # 验证是否为Swagger文档
        if 'swagger' not in api_spec or api_spec['swagger'] != '2.0':
            raise ValueError("文档不符合Swagger 2.0规范")
        
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
                            'schema': {}
                        }
                        
                        # Swagger 2.0中，body类型参数包含schema
                        if param.get('in') == 'body' and 'schema' in param:
                            param_info['schema'] = param['schema']
                        else:
                            # 对于非body参数，构建简化的schema
                            param_info['schema'] = {
                                'type': param.get('type', 'string'),
                                'format': param.get('format', None),
                                'enum': param.get('enum', None)
                            }
                            
                        endpoint['parameters'].append(param_info)
                    
                    # 在Swagger 2.0中，请求体通过parameters中的body类型参数定义
                    body_params = [p for p in operation.get('parameters', []) if p.get('in') == 'body']
                    if body_params:
                        body_param = body_params[0]
                        endpoint['requestBody'] = {
                            'content_type': 'application/json',  # Swagger 2.0默认
                            'schema': body_param.get('schema', {}),
                            'required': body_param.get('required', False)
                        }
                    
                    # 提取响应信息
                    for status_code, response in operation.get('responses', {}).items():
                        response_info = {
                            'status_code': status_code,
                            'description': response.get('description', ''),
                            'content_type': 'application/json',  # Swagger 2.0默认
                            'schema': response.get('schema', {})
                        }
                        endpoint['responses'].append(response_info)
                    
                    api_info['endpoints'].append(endpoint)
        
        return api_info 