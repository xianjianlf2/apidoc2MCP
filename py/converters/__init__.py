#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API数据转换器模块
将解析后的API数据转换为标准格式(OpenAPI)
"""

import os
import json
import hashlib
from utils.logger import get_logger

logger = get_logger()

# 缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def convert_to_standard_format(api_data):
    """
    将解析后的API数据转换为标准格式(OpenAPI)
    
    Args:
        api_data: 解析后的API数据
    
    Returns:
        标准格式的API数据
    """
    # 检查输入数据是否有效
    if not api_data:
        logger.warning("⚠️ 输入的API数据为空，无法转换")
        return None
    
    # 生成缓存键
    cache_key = _generate_cache_key(api_data)
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    # 检查缓存
    if os.path.exists(cache_file):
        logger.info("🔄 从缓存加载转换结果")
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ 缓存加载失败: {str(e)}")
    
    # 检查数据格式
    data_format = _detect_format(api_data)
    logger.info(f"🔍 检测到API数据格式: {data_format}")
    
    # 根据检测到的格式进行转换
    if data_format == 'openapi':
        # 数据已经是OpenAPI格式，直接返回
        result = api_data
        logger.info("✅ 数据已是OpenAPI格式，无需转换")
    elif data_format == 'swagger':
        # 转换Swagger到OpenAPI 3.0
        result = _convert_swagger_to_openapi(api_data)
        logger.info("🔄 Swagger数据已转换为OpenAPI格式")
    elif data_format == 'custom':
        # 转换自定义格式到OpenAPI
        result = _convert_custom_to_openapi(api_data)
        logger.info("🔄 自定义格式数据已转换为OpenAPI格式")
    elif data_format == 'unstructured':
        # 非结构化数据需要使用LLM处理
        logger.warning("⚠️ 检测到非结构化数据，标记为TODO")
        print(api_data)
        result = _mark_unstructured_as_todo(api_data)
    else:
        # 未知格式
        logger.warning(f"⚠️ 未知的API数据格式: {data_format}，尝试通用转换")
        result = _convert_to_openapi_generic(api_data)
    
    # 验证转换结果是否符合OpenAPI规范
    if _validate_openapi(result):
        # 缓存转换结果
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info("💾 转换结果已缓存")
        except Exception as e:
            logger.warning(f"⚠️ 缓存写入失败: {str(e)}")
    else:
        logger.warning("⚠️ 转换结果不符合OpenAPI规范，跳过缓存")
    
    return result

def _generate_cache_key(api_data):
    """
    为API数据生成缓存键
    
    Args:
        api_data: API数据
    
    Returns:
        缓存键字符串
    """
    # 将API数据转换为JSON字符串
    try:
        data_str = json.dumps(api_data, sort_keys=True)
    except:
        # 如果无法序列化，则使用字符串表示
        data_str = str(api_data)
    
    # 计算MD5哈希值作为缓存键
    return hashlib.md5(data_str.encode('utf-8')).hexdigest()

def _detect_format(api_data):
    """
    检测API数据的格式
    
    Args:
        api_data: API数据
    
    Returns:
        数据格式字符串: 'openapi', 'swagger', 'custom', 'unstructured'
    """
    # 检查是否为字典类型
    if not isinstance(api_data, dict):
        return 'unstructured'
    
    # 检查OpenAPI 3.x
    if 'openapi' in api_data and api_data.get('openapi', '').startswith('3.'):
        return 'openapi'
    
    # 检查Swagger 2.0
    if 'swagger' in api_data and api_data.get('swagger') == '2.0':
        return 'swagger'
    
    # 检查是否为我们自定义的中间格式
    if 'endpoints' in api_data and isinstance(api_data.get('endpoints'), list):
        return 'custom'
    
    # 其他情况视为非结构化数据
    return 'unstructured'

def _convert_swagger_to_openapi(swagger_data):
    """
    将Swagger 2.0数据转换为OpenAPI 3.0格式
    
    Args:
        swagger_data: Swagger 2.0数据
    
    Returns:
        OpenAPI 3.0格式的数据
    """
    # 创建OpenAPI 3.0基本结构
    openapi_data = {
        'openapi': '3.0.0',
        'info': swagger_data.get('info', {'title': 'API', 'version': '1.0.0'}),
        'paths': {},
        'components': {
            'schemas': swagger_data.get('definitions', {}),
            'parameters': swagger_data.get('parameters', {}),
            'responses': swagger_data.get('responses', {})
        }
    }
    
    # 转换路径
    paths = swagger_data.get('paths', {})
    for path, path_item in paths.items():
        openapi_data['paths'][path] = {}
        
        for method, operation in path_item.items():
            if method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                # 转换参数
                parameters = []
                for param in operation.get('parameters', []):
                    if param.get('in') != 'body':
                        # 非body参数直接添加
                        parameters.append(param)
                    else:
                        # body参数转换为requestBody
                        schema = param.get('schema', {})
                        openapi_data['paths'][path][method] = {
                            **operation,
                            'requestBody': {
                                'content': {
                                    'application/json': {
                                        'schema': schema
                                    }
                                },
                                'required': param.get('required', False)
                            }
                        }
                
                # 更新操作定义
                if 'requestBody' not in openapi_data['paths'][path].get(method, {}):
                    openapi_data['paths'][path][method] = {
                        **operation,
                        'parameters': parameters
                    }
                else:
                    openapi_data['paths'][path][method]['parameters'] = parameters
                
                # 删除旧的parameters字段
                if 'parameters' in operation and not parameters:
                    del openapi_data['paths'][path][method]['parameters']
    
    return openapi_data

def _convert_custom_to_openapi(custom_data):
    """
    将自定义格式数据转换为OpenAPI 3.0格式
    
    Args:
        custom_data: 自定义格式数据
    
    Returns:
        OpenAPI 3.0格式的数据
    """
    # 创建OpenAPI 3.0基本结构
    openapi_data = {
        'openapi': '3.0.0',
        'info': {
            'title': custom_data.get('title', 'API'),
            'version': custom_data.get('version', '1.0.0'),
            'description': custom_data.get('description', '')
        },
        'paths': {}
    }
    
    # 转换endpoints
    for endpoint in custom_data.get('endpoints', []):
        path = endpoint.get('path')
        method = endpoint.get('method', 'get').lower()
        
        if not path:
            continue
        
        # 确保路径存在
        if path not in openapi_data['paths']:
            openapi_data['paths'][path] = {}
        
        # 创建操作对象
        operation = {
            'summary': endpoint.get('summary', ''),
            'description': endpoint.get('description', ''),
            'operationId': endpoint.get('operationId', ''),
            'parameters': [],
            'responses': {
                '200': {
                    'description': 'Successful operation',
                    'content': {}
                }
            }
        }
        
        # 添加参数
        for param in endpoint.get('parameters', []):
            openapi_param = {
                'name': param.get('name', ''),
                'in': param.get('in', 'query'),
                'description': param.get('description', ''),
                'required': param.get('required', False),
                'schema': param.get('schema', {'type': 'string'})
            }
            operation['parameters'].append(openapi_param)
        
        # 添加请求体
        if endpoint.get('requestBody'):
            operation['requestBody'] = {
                'content': {
                    endpoint.get('requestBody', {}).get('content_type', 'application/json'): {
                        'schema': endpoint.get('requestBody', {}).get('schema', {})
                    }
                },
                'required': endpoint.get('requestBody', {}).get('required', False)
            }
        
        # 添加响应
        for response in endpoint.get('responses', []):
            status_code = response.get('status_code', '200')
            operation['responses'][status_code] = {
                'description': response.get('description', ''),
                'content': {}
            }
            
            if response.get('content_type') and response.get('schema'):
                operation['responses'][status_code]['content'][response.get('content_type')] = {
                    'schema': response.get('schema')
                }
        
        # 添加操作到路径
        openapi_data['paths'][path][method] = operation
    
    return openapi_data

def _mark_unstructured_as_todo(unstructured_data):
    """
    将非结构化数据标记为TODO，以便后续使用LLM处理
    
    Args:
        unstructured_data: 非结构化数据
    
    Returns:
        标记了TODO的中间格式数据
    """
    # 创建一个包含TODO标记的结构
    result = {
        'title': 'Unstructured API Data',
        'version': '1.0.0',
        'description': 'This API data is unstructured and needs to be processed by LLM',
        'todo': True,
        'original_data': unstructured_data,
        'endpoints': []
    }
    
    # 如果有可能的端点信息，尝试提取
    if isinstance(unstructured_data, dict) and 'paths' in unstructured_data:
        # TODO: 从paths中提取可能的端点信息
        pass
    
    logger.info("🤖 需要使用LLM处理非结构化数据，已标记为TODO")
    return result

def _convert_to_openapi_generic(unknown_data):
    """
    尝试将未知格式的数据通用转换为OpenAPI格式
    
    Args:
        unknown_data: 未知格式的数据
    
    Returns:
        尽可能转换为OpenAPI格式的数据
    """
    # 创建基本的OpenAPI结构
    openapi_data = {
        'openapi': '3.0.0',
        'info': {
            'title': 'Unknown API',
            'version': '1.0.0',
            'description': 'Converted from unknown format'
        },
        'paths': {}
    }
    
    # 根据数据结构尝试提取API信息
    if isinstance(unknown_data, dict):
        # 提取信息字段
        if 'info' in unknown_data and isinstance(unknown_data['info'], dict):
            openapi_data['info'] = unknown_data['info']
        else:
            for key in ['title', 'version', 'description']:
                if key in unknown_data:
                    openapi_data['info'][key] = unknown_data[key]
        
        # 尝试提取路径
        if 'paths' in unknown_data and isinstance(unknown_data['paths'], dict):
            openapi_data['paths'] = unknown_data['paths']
        elif 'apis' in unknown_data and isinstance(unknown_data['apis'], list):
            # 处理可能的API列表
            for api in unknown_data['apis']:
                if 'path' in api and 'operations' in api:
                    path = api['path']
                    openapi_data['paths'][path] = {}
                    for op in api['operations']:
                        if 'method' in op:
                            method = op['method'].lower()
                            del op['method']
                            openapi_data['paths'][path][method] = op
    
    # 如果没有提取到任何路径，标记为TODO
    if not openapi_data['paths']:
        logger.warning("⚠️ 无法从未知格式中提取API路径，标记为TODO")
        return _mark_unstructured_as_todo(unknown_data)
    
    return openapi_data

def _validate_openapi(openapi_data):
    """
    验证数据是否符合OpenAPI规范
    
    Args:
        openapi_data: 待验证的OpenAPI数据
    
    Returns:
        布尔值，是否符合OpenAPI规范
    """
    # 基本验证
    if not isinstance(openapi_data, dict):
        return False
    
    # 检查必要字段
    required_fields = ['openapi', 'info', 'paths']
    for field in required_fields:
        if field not in openapi_data:
            return False
    
    # 检查版本
    if not isinstance(openapi_data.get('openapi'), str) or not openapi_data['openapi'].startswith('3.'):
        return False
    
    # 检查info
    info = openapi_data.get('info', {})
    if not isinstance(info, dict) or 'title' not in info or 'version' not in info:
        return False
    
    # 检查paths
    paths = openapi_data.get('paths', {})
    if not isinstance(paths, dict):
        return False
    
    return True 