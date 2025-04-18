#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP服务生成流水线
整合解析器、转换器和生成器，提供完整的API文档到MCP服务的转换流程
"""

import os
import time
from parsers import parse_document
from converters import convert_to_standard_format
from generators import generate_mcp_service
from utils.logger import get_logger

logger = get_logger()


class MCPPipeline:
    """
    MCP服务生成流水线类
    整合解析、转换和生成三个阶段
    """

    def __init__(self, output_dir="./O_MCP_SERVER_LIST"):
        """
        初始化MCP流水线

        Args:
            output_dir: 默认输出目录
        """
        self.output_dir = output_dir
        self.metrics = {
            "parse_time": 0,
            "convert_time": 0,
            "generate_time": 0,
            "total_time": 0,
            "endpoints_count": 0,
            "incomplete_endpoints": 0
        }

    def run(self, input_path, format="auto", service_name=None):
        """
        运行完整的MCP服务生成流水线

        Args:
            input_path: 输入文档路径，可以是URL或文件路径
            format: 输入文档格式，可选值为'swagger', 'openapi', 'markdown', 'auto'
            service_name: MCP服务名称，如果指定，将作为服务名并添加到输出目录后

        Returns:
            元组 (是否成功, 输出目录路径, 指标数据)
        """
        start_time = time.time()

        try:
            # 1. 解析阶段
            logger.info(f"📄 [1/3] 正在解析文档: {input_path}，格式: {format}")
            parse_start = time.time()
            api_data = self._parse(input_path, format)
            parse_end = time.time()
            self.metrics["parse_time"] = parse_end - parse_start

            if not api_data:
                logger.error("❌ 文档解析失败，流程终止")
                return False, None, self.metrics

            # 2. 转换阶段
            logger.info("🔄 [2/3] 正在转换为OpenAPI标准格式...")
            convert_start = time.time()
            standard_format = self._convert(api_data)
            convert_end = time.time()
            self.metrics["convert_time"] = convert_end - convert_start

            if not standard_format:
                logger.error("❌ 格式转换失败，流程终止")
                return False, None, self.metrics

            # 3. 处理服务名称
            output_dir = self._process_service_name(
                standard_format, service_name)

            # 4. 生成阶段
            logger.info(f"🚀 [3/3] 正在生成MCP服务到: {output_dir}")
            generate_start = time.time()
            success, metrics = self._generate(standard_format, output_dir)
            generate_end = time.time()
            self.metrics["generate_time"] = generate_end - generate_start

            # 更新指标
            self.metrics.update(metrics)
            self.metrics["total_time"] = time.time() - start_time

            if success:
                logger.info(f"✅ MCP服务生成完成，已写入到目录: {output_dir}")
                self._show_metrics()
                self._show_startup_guide(output_dir)
                return True, output_dir, self.metrics
            else:
                logger.error("❌ MCP服务生成失败")
                return False, output_dir, self.metrics

        except Exception as e:
            logger.error(f"❌ 流水线执行出错: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())

            self.metrics["total_time"] = time.time() - start_time
            return False, None, self.metrics

    def _parse(self, input_path, format):
        """解析阶段"""
        try:
            return parse_document(input_path, format)
        except Exception as e:
            logger.error(f"❌ 解析阶段出错: {str(e)}")
            return None

    def _convert(self, api_data):
        """转换阶段"""
        try:
            return convert_to_standard_format(api_data)
        except Exception as e:
            logger.error(f"❌ 转换阶段出错: {str(e)}")
            return None

    def _process_service_name(self, standard_format, service_name):
        """处理服务名称"""
        if service_name:
            logger.info(f"🏷️ 使用指定的服务名称: {service_name}")
            # 设置服务名称
            if 'title' not in standard_format:
                standard_format['title'] = service_name
            else:
                standard_format['original_title'] = standard_format.get(
                    'title')
                standard_format['title'] = service_name

            # 将服务名添加到输出目录
            output_dir = os.path.join(self.output_dir, service_name)
        else:
            # 尝试从标准格式中获取服务名
            if 'title' in standard_format and standard_format['title']:
                service_title = standard_format['title']
                # 清理标题，使其适合作为目录名
                service_title = service_title.replace(' ', '_').lower()
                output_dir = os.path.join(self.output_dir, service_title)
                logger.info(f"🏷️ 使用API标题作为服务名称: {service_title}")
            else:
                output_dir = self.output_dir

        # windows下替换路径
        if os.name == 'nt':
            output_dir = output_dir.replace('\\', '/')
        return output_dir

    def _generate(self, standard_format, output_dir):
        """生成阶段"""
        try:
            success = generate_mcp_service(standard_format, output_dir)

            # 获取生成的信息
            metrics = {
                "endpoints_count": 0,
                "incomplete_endpoints": 0
            }

            # 如果是OpenAPI格式，从paths统计端点数量
            if 'paths' in standard_format:
                endpoint_count = 0
                for path_item in standard_format['paths'].values():
                    for method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                        if method in path_item:
                            endpoint_count += 1
                metrics["endpoints_count"] = endpoint_count
            elif 'endpoints' in standard_format:
                metrics["endpoints_count"] = len(standard_format['endpoints'])

            return success, metrics
        except Exception as e:
            logger.error(f"❌ 生成阶段出错: {str(e)}")
            return False, {}

    def _show_metrics(self):
        """显示性能指标"""
        # 合并指标数据到一个info log
        logger.info("\n📊 流水线执行指标:"
                    + f"\n总执行时间: {self.metrics['total_time']:.2f}秒"
                    + f"\n总执行时间: {self.metrics['total_time']:.2f}秒"
                    + f"\n解析阶段: {self.metrics['parse_time']:.2f}秒"
                    + f"\n转换阶段: {self.metrics['convert_time']:.2f}秒"
                    + f"\n生成阶段: {self.metrics['generate_time']:.2f}秒"
                    + f"\n端点总数: {self.metrics['endpoints_count']}个")

    def _show_startup_guide(self, output_dir):
        """显示启动指南"""
        mcp_server_path = os.path.join(output_dir, 'mcp_server.py')
        # windows下替换路径
        if os.name == 'nt':
            mcp_server_path = mcp_server_path.replace('\\', '/')
        logger.info(
            f"""\n🚀 启动MCP服务:\n
1. 直接运行生成的Python文件
> python {mcp_server_path}

2. 使用MCP CLI工具运行测试
> mcp dev {mcp_server_path}

3. 使用环境变量自定义API基础URL
> API_BASE_URL=https://your-api-base-url python {mcp_server_path}"""
        )


def run_pipeline(input_path, format="auto", output_dir="./O_MCP_SERVER_LIST", service_name=None):
    """
    运行MCP服务生成流水线的便捷函数

    Args:
        input_path: 输入文档路径，可以是URL或文件路径
        format: 输入文档格式，可选值为'swagger', 'openapi', 'markdown', 'auto'
        output_dir: 输出目录
        service_name: MCP服务名称，如果指定，将作为服务名并添加到输出目录后

    Returns:
        元组 (是否成功, 输出目录路径, 指标数据)
    """
    pipeline = MCPPipeline(output_dir)
    return pipeline.run(input_path, format, service_name)
