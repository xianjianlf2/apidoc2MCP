#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
apidoc2MCP 主程序
用于将接口文档转换为MCP服务
"""

import argparse
import sys
import os
from utils.logger import init_logger, get_logger
from pipeline import run_pipeline

init_logger()
logger = get_logger()


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='将API文档转换为MCP服务')
    parser.add_argument('input', help='输入文档路径，可以是URL或文件路径')
    parser.add_argument('--format', choices=['swagger', 'openapi', 'markdown', 'html', 'auto'],
                        default='auto', help='输入文档格式，默认为自动检测')
    parser.add_argument('--output', default='./O_MCP_SERVER_LIST', help='输出目录')
    parser.add_argument('--name', help='MCP服务名称，如果指定，将作为服务名并添加到输出目录后')
    args = parser.parse_args()

    try:
        # 使用流水线执行完整的转换过程
        success, output_dir, metrics = run_pipeline(
            input_path=args.input,
            format=args.format,
            output_dir=args.output,
            service_name=args.name
        )

        # 根据执行结果返回状态码
        return 0 if success else 1

    except Exception as e:
        logger.error(f"❌ 错误：{str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1


if __name__ == '__main__':
    sys.exit(main())
