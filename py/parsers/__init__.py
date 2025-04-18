#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API文档解析器模块
支持解析不同格式的API文档
"""

from .swagger import SwaggerParser
from .openapi import OpenAPIParser
from .markdown import MarkdownParser
from .crawler import CrawlerParser
from utils.logger import get_logger

logger = get_logger()


def parse_document(input_path, format_type='auto'):
    """
    解析API文档

    Args:
        input_path: 文档路径，可以是URL或文件路径
        format_type: 文档格式，可以是'swagger', 'openapi', 'markdown', 'html'或'auto'

    Returns:
        解析后的API数据
    """
    # 根据文档格式选择合适的解析器
    if format_type == 'auto':
        # 自动检测文档格式
        format_type = detect_format(input_path)

    parser_map = {
        'swagger': SwaggerParser,
        'openapi': OpenAPIParser,
        'markdown': MarkdownParser,
        'html': CrawlerParser,
        'crawler': CrawlerParser
    }

    if format_type not in parser_map:
        logger.warning(f"⚠️ 不支持的文档格式: {format_type}，尝试使用爬虫解析")
        format_type = 'crawler'

    logger.info(f"📄 使用 {format_type} 解析器解析文档")
    parser_class = parser_map[format_type]
    parser = parser_class()

    try:
        # 解析文档
        result = parser.parse(input_path)

        # 检查解析是否成功
        if result and (
            (isinstance(result, dict) and ('paths' in result or 'endpoints' in result))
            or (isinstance(result, list) and len(result) > 0)
        ):
            logger.info(f"✅ 成功解析文档，使用 {format_type} 格式")
            return result
        else:
            # 如果解析结果为空，尝试使用爬虫解析
            if format_type != 'crawler':
                logger.warning(f"⚠️ {format_type} 解析结果为空，尝试使用爬虫解析")
                crawler = CrawlerParser()
                crawler_result = crawler.parse(input_path)

                # 检查爬虫解析是否成功
                if crawler_result and 'paths' in crawler_result and crawler_result['paths']:
                    logger.info("✅ 成功使用爬虫解析文档")
                    return crawler_result

            logger.warning("⚠️ 解析结果为空")
            return result
    except Exception as e:
        logger.error(f"❌ 解析文档出错: {str(e)}")

        # 如果不是爬虫解析，尝试使用爬虫解析
        if format_type != 'crawler':
            logger.info("🔄 尝试使用爬虫解析文档")
            try:
                crawler = CrawlerParser()
                crawler_result = crawler.parse(input_path)

                # 检查爬虫解析是否成功
                if crawler_result and 'paths' in crawler_result and crawler_result['paths']:
                    logger.info("✅ 成功使用爬虫解析文档")
                    return crawler_result
            except Exception as crawler_error:
                logger.error(f"❌ 爬虫解析文档出错: {str(crawler_error)}")

        # 重新抛出原始异常
        raise


def detect_format(input_path):
    """
    自动检测文档格式

    Args:
        input_path: 文档路径

    Returns:
        检测到的文档格式
    """
    # 根据文件扩展名或内容判断文档格式
    if input_path.lower().endswith(('.json', '.yaml', '.yml')):
        # 尝试区分Swagger和OpenAPI
        try:
            import json
            import yaml
            import requests

            # 加载文档内容
            if input_path.startswith(('http://', 'https://')):
                response = requests.get(input_path)
                content = response.text
            else:
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()

            # 解析内容
            if input_path.lower().endswith('.json'):
                data = json.loads(content)
            else:
                data = yaml.safe_load(content)

            # 检查是否为Swagger 2.0
            if 'swagger' in data and data['swagger'] == '2.0':
                return 'swagger'

            # 检查是否为OpenAPI 3.x
            if 'openapi' in data and data['openapi'].startswith('3.'):
                return 'openapi'

            # 返回默认值
            return 'openapi'
        except Exception:
            # 解析失败，返回默认值
            return 'openapi'
    elif input_path.lower().endswith('.md'):
        return 'markdown'
    elif input_path.lower().endswith(('.html', '.htm')):
        return 'html'
    elif input_path.startswith(('http://', 'https://')):
        # 对于URL，尝试检测内容类型
        try:
            import requests
            response = requests.head(input_path)
            content_type = response.headers.get('Content-Type', '')

            if 'json' in content_type:
                # 尝试获取并解析JSON
                response = requests.get(input_path)
                data = response.json()

                # 检查是否为Swagger 2.0或OpenAPI 3.x
                if 'swagger' in data and data['swagger'] == '2.0':
                    return 'swagger'
                elif 'openapi' in data and data['openapi'].startswith('3.'):
                    return 'openapi'

                return 'openapi'
            elif 'text/html' in content_type:
                return 'html'
            elif 'text/markdown' in content_type:
                return 'markdown'
        except Exception:
            # 如果检测失败，默认使用爬虫解析
            return 'crawler'

    # 默认使用爬虫尝试解析
    return 'crawler'
