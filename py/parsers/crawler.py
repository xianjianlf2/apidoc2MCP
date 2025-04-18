
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import urlparse
from .base import BaseParser
from utils.logger import get_logger

logger = get_logger()


class CrawlerParser(BaseParser):
    """
    API文档爬虫解析器类
    尝试从HTML文档中结构化地提取API接口或操作信息。
    """

    def __init__(self):
        """初始化爬虫解析器"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # 用于存储提取到的端点/操作信息
        self.extracted_operations = []
        # 常见的可能包含API或操作信息的HTML元素选择器
        # 增加了对代码块、标题等的关注
        self.operation_selectors = [
            'pre', 'code',  # 代码块优先
            'div.endpoint', 'section.api', 'article.endpoint',  # 特定容器
            'table.api', 'table.endpoints',  # 表格
            'h2', 'h3', 'h4'  # 标题（后续会分析其内容和相邻元素）
        ]
        # 用于提取URL路径、HTTP方法、命令行模式的正则表达式
        # 稍微放宽路径匹配，允许更复杂的字符
        self.path_pattern = re.compile(r'((?:/[a-zA-Z0-9{}/?=&%.:\-_~]+)+)')
        self.method_pattern = re.compile(
            r'\b(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\b', re.IGNORECASE)
        self.cmd_pattern = re.compile(
            r'^(?:python|pip|mcp|docker|kubectl|aws|gcloud|az|.\/|bash)\s+.*', re.IGNORECASE)
        self.param_pattern = re.compile(r'\{([^}]+)\}')  # 路径参数 {param}
        # 命令行参数 --arg=<val>, -a, <placeholder>
        self.arg_pattern = re.compile(
            r'(--[a-zA-Z0-9\-]+(?:=[^ ]+)?)|(-[a-zA-Z][a-zA-Z0-9\-]*)|(<[^>]+>)')

    def parse(self, input_path):
        """
        解析API文档网页或本地HTML文件

        Args:
            input_path: 文档URL或本地HTML文件路径

        Returns:
            包含提取到的操作信息的列表，每个元素是一个字典。
            例如: [{'type': 'http', 'path': '/users/{id}', 'method': 'GET', 'description': '...', 'parameters': [...]},
                   {'type': 'cmd', 'command': 'python main.py ...', 'description': '...', 'parameters': [...]}]
            如果无法解析或提取，返回空列表。
        """
        logger.info(f"🕸️ 开始从 {input_path} 抓取操作信息")
        self.extracted_operations = []  # 重置

        try:
            content = self.load_content(input_path)
            soup = BeautifulSoup(content, 'html.parser')

            # 1. 提取页面基本信息 (可选，暂不纳入核心提取结果)
            page_info = self._extract_page_info(soup)
            logger.info(f"📄 页面标题: {page_info.get('title', 'N/A')}")

            # 2. 结构化提取
            self._structured_extraction(soup)

            # 3. 如果结构化提取效果不佳，尝试基于文本的提取 (作为补充)
            if not self.extracted_operations:
                logger.info("🤔 结构化提取未找到明确操作，尝试基于文本内容提取...")
                self._text_based_extraction(soup)

            if not self.extracted_operations:
                logger.warning("⚠️ 未找到任何可识别的操作或端点信息")
            else:
                logger.info(
                    f"✅ 提取到 {len(self.extracted_operations)} 个可能的操作/端点")

            return self.extracted_operations

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ HTTP请求失败: {e}")
            return []
        except FileNotFoundError:
            logger.error(f"❌ 文件未找到: {input_path}")
            return []
        except Exception as e:
            logger.error(f"❌ 解析HTML时发生错误: {e}", exc_info=True)
            return []

    def _extract_page_info(self, soup):
        """提取页面标题等基本信息"""
        info = {}
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            info['title'] = title_tag.string.strip()
        # 可以扩展提取 meta description 等
        return info

    def _structured_extraction(self, soup):
        """尝试通过常见的HTML结构提取信息"""
        processed_elements = set()  # 防止重复处理

        for selector in self.operation_selectors:
            elements = soup.select(selector)
            for element in elements:
                # 跳过已经处理过的元素及其子元素
                if any(processed_el in element.parents or processed_el == element for processed_el in processed_elements):
                    continue

                logger.debug(
                    f"🔍 正在处理元素: <{element.name}> (Selector: {selector})")
                extracted = False
                if element.name in ['pre', 'code']:
                    extracted = self._process_code_block(element)
                elif element.name == 'table':
                    extracted = self._process_table(element)
                elif element.name.startswith('h'):  # 处理标题及其后续内容
                    extracted = self._process_heading_section(element)
                elif element.name in ['div', 'section', 'article']:  # 处理通用容器
                    extracted = self._process_container(element)

                if extracted:
                    processed_elements.add(element)  # 标记为已处理

    def _text_based_extraction(self, soup):
        """从页面纯文本中提取信息 (效果可能较差)"""
        # 实现基于正则表达式的简单文本提取逻辑（此处省略具体实现细节）
        # 这种方法准确率较低，容易误判，仅作为补充
        pass

    def _process_code_block(self, element):
        """处理 <pre> 或 <code> 块"""
        text = element.get_text("\n", strip=True)
        lines = text.split('\n')
        extracted_count = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 尝试识别HTTP请求示例 (curl, httpie, etc.) 或 API路径/方法
            method = self._find_method(line)
            path = self._find_path(line)
            cmd_match = self.cmd_pattern.match(line)

            if cmd_match:
                operation = self._create_operation_entry('cmd', command=line)
                # 尝试从相邻元素获取描述
                desc = self._find_neighbor_description(element)
                if desc:
                    operation['description'] = desc
                # 提取参数
                operation['parameters'] = self._extract_cmd_args(line)
                self.extracted_operations.append(operation)
                logger.debug(f"  -> 提取到 CMD: {line[:80]}...")
                extracted_count += 1
            elif path:
                operation = self._create_operation_entry(
                    'http', path=path, method=(method if method else 'get'))
                # 尝试从相邻元素获取描述
                desc = self._find_neighbor_description(element)
                if desc:
                    operation['description'] = desc
                # 提取参数
                operation['parameters'] = self._extract_http_params(
                    path, element.get_text())
                self.extracted_operations.append(operation)
                logger.debug(
                    f"  -> 提取到 HTTP (from code): {operation.get('method','').upper()} {path}")
                extracted_count += 1
            elif method:  # 如果只找到方法，也记录下来，可能后续有路径
                operation = self._create_operation_entry(
                    'http', method=method, description=f"Found method '{method}' in code block: {line[:50]}...")
                self.extracted_operations.append(operation)
                logger.debug(f"  -> 提取到潜在 HTTP Method (from code): {method}")
                extracted_count += 1
        return extracted_count > 0

    def _process_table(self, element):
        """处理 <table> 元素"""
        # 提取表头和数据行，分析每一行尝试组合成API信息
        # (省略详细实现，逻辑会比较复杂，需要判断列的含义)
        logger.debug("  -> 跳过表格处理 (未实现)")
        return False  # 标记为未处理

    def _process_heading_section(self, element):
        """处理标题 (h2-h4) 及其紧随其后的内容"""
        heading_text = element.get_text(strip=True)
        method = self._find_method(heading_text)
        path = self._find_path(heading_text)
        cmd_match = self.cmd_pattern.match(heading_text)

        # 如果标题本身包含API信息
        if path or cmd_match:
            description_parts = []
            parameters = []
            # 收集紧随其后的描述性内容 (<p>, <ul>, <ol>, <pre>, <code>)
            sibling = element.find_next_sibling()
            while sibling and isinstance(sibling, Tag) and sibling.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if sibling.name == 'p':
                    description_parts.append(sibling.get_text(strip=True))
                elif sibling.name in ['ul', 'ol']:
                    # 尝试从列表中提取参数
                    for li in sibling.find_all('li'):
                        param_text = li.get_text(strip=True)
                        # 简单的参数格式检测 (e.g., "param_name: description")
                        match = re.match(
                            r'^([\w\-]+)\s*[:\-]\s*(.*)', param_text)
                        if match:
                            param_name, param_desc = match.groups()
                            parameters.append(
                                {'name': param_name.strip(), 'description': param_desc.strip()})
                        else:
                            description_parts.append(param_text)  # 否则视为描述
                elif sibling.name in ['pre', 'code']:
                    # 如果后面紧跟着代码块，也加入描述或尝试提取更多信息
                    description_parts.append(
                        f"Example:\n{sibling.get_text(strip=True)}")
                    # 可以调用 _process_code_block 处理这个代码块，但要注意避免重复添加
                sibling = sibling.find_next_sibling()

            description = "\n".join(description_parts).strip()

            if cmd_match:
                operation = self._create_operation_entry(
                    'cmd', command=heading_text, description=description)
                operation['parameters'] = self._extract_cmd_args(
                    heading_text) + parameters  # 合并提取到的参数
                self.extracted_operations.append(operation)
                logger.debug(f"  -> 提取到 CMD (from heading): {heading_text}")
                return True
            elif path:
                operation = self._create_operation_entry('http', path=path, method=(
                    method if method else 'get'), description=description)
                operation['parameters'] = self._extract_http_params(
                    path, description) + parameters  # 合并
                self.extracted_operations.append(operation)
                logger.debug(
                    f"  -> 提取到 HTTP (from heading): {operation.get('method','').upper()} {path}")
                return True
        return False

    def _process_container(self, element):
        """处理 <div>, <section>, <article> 等容器元素"""
        # 尝试在容器内部查找API特征，例如查找包含HTTP方法和路径的文本块
        text_content = element.get_text(" ", strip=True)
        method = self._find_method(text_content)
        path = self._find_path(text_content)

        if method and path:
            # 如果容器内同时包含方法和路径，可能是一个API描述块
            description = text_content  # 使用整个容器文本作为初步描述
            operation = self._create_operation_entry(
                'http', path=path, method=method, description=description)
            # 可以在这里添加更复杂的逻辑来查找容器内的参数描述
            operation['parameters'] = self._extract_http_params(
                path, text_content)
            self.extracted_operations.append(operation)
            logger.debug(
                f"  -> 提取到 HTTP (from container): {method.upper()} {path}")
            return True  # 标记此容器已处理

        # 也可以递归处理容器内的子元素，但要注意效率和避免重复
        # for child in element.find_all(recursive=False):
        #     if isinstance(child, Tag):
        #         self._structured_extraction(child) # 简化处理，可能需要更复杂的逻辑

        return False

    def _find_method(self, text):
        """在文本中查找HTTP方法"""
        match = self.method_pattern.search(text)
        return match.group(1).lower() if match else None

    def _find_path(self, text):
        """在文本中查找可能的API路径"""
        # 优先匹配更长的、包含多个斜杠的路径
        matches = self.path_pattern.findall(text)
        if not matches:
            return None
        # 选择看起来最像API路径的匹配项（例如，包含多个斜杠）
        best_match = max(matches, key=lambda p: p.count('/'))
        # 过滤掉一些明显不是路径的（比如只有一个斜杠且很短）
        if best_match.count('/') >= 1 and len(best_match) > 2:
            # 移除可能的尾随标点
            best_match = re.sub(r'[.,;:)\s]+$', '', best_match)
            return best_match
        return None

    def _find_neighbor_description(self, element):
        """尝试查找元素前面或后面的描述性文本"""
        desc_parts = []
        # 向前查找 P 标签
        prev = element.find_previous_sibling()
        if prev and isinstance(prev, Tag) and prev.name == 'p':
            desc_parts.insert(0, prev.get_text(strip=True))
        # 向后查找 P 标签
        next_el = element.find_next_sibling()
        if next_el and isinstance(next_el, Tag) and next_el.name == 'p':
            desc_parts.append(next_el.get_text(strip=True))
        return "\n".join(desc_parts) if desc_parts else None

    def _extract_http_params(self, path, context_text):
        """从路径和上下文文本中提取HTTP参数"""
        params = []
        # 1. 提取路径参数
        path_params = self.param_pattern.findall(path)
        for p_name in path_params:
            params.append({
                'name': p_name,
                'in': 'path',
                'required': True,
                'description': f'Path parameter: {p_name}',
                'schema': {'type': 'string'}  # 默认类型
            })

        # 2. TODO: 从上下文文本中提取查询参数、请求体参数等 (需要更复杂的NLP或规则)
        # 例如查找 "Parameters:", "Query Parameters:", "Request Body:", 或表格/列表中的参数描述
        return params

    def _extract_cmd_args(self, command_line):
        """从命令行文本中提取参数"""
        args = []
        matches = self.arg_pattern.findall(command_line)
        # findall 返回的是元组列表，每个元组对应一个捕获组
        for match_tuple in matches:
            arg = next((m for m in match_tuple if m), None)  # 找到非空的匹配项
            if arg:
                param_name = arg
                description = f"Command-line argument: {arg}"
                is_placeholder = arg.startswith('<') and arg.endswith('>')
                is_option = arg.startswith('-')

                if is_option:
                    param_name = arg.split('=', 1)[0]  # 处理 --arg=value 形式
                    description = f"Command-line option: {param_name}"
                elif is_placeholder:
                    param_name = arg[1:-1]  # 移除尖括号
                    description = f"Command-line placeholder: {param_name}"

                args.append({
                    'name': param_name,
                    'in': 'argument' if not is_option else 'option',
                    'required': is_placeholder,  # 简单假设占位符是必需的
                    'description': description,
                    'schema': {'type': 'string'}
                })
        return args

    def _create_operation_entry(self, op_type, **kwargs):
        """创建标准化的操作条目字典"""
        entry = {'type': op_type}
        entry.update(kwargs)
        return entry

# --- Helper for loading content (kept from BaseParser logic) ---
    def is_url(self, input_path):
        """判断输入是否为URL"""
        return input_path.startswith('http://') or input_path.startswith('https://')

    def load_content(self, input_path):
        """加载文档内容"""
        if self.is_url(input_path):
            logger.debug(f"  -> 发送HTTP GET请求到: {input_path}")
            response = requests.get(
                input_path, headers=self.headers, timeout=15)
            response.raise_for_status()
            # 尝试检测编码，优先使用 headers，然后是 meta charset，最后是 chardet
            content_type = response.headers.get('content-type', '').lower()
            charset = requests.utils.get_encoding_from_headers(
                response.headers)
            if not charset and 'text/html' in content_type:
                # 检查 meta charset
                # Use a lenient initial parse
                soup = BeautifulSoup(
                    response.content, 'html.parser', from_encoding='iso-8859-1')
                meta_charset = soup.find('meta', charset=True)
                if meta_charset:
                    charset = meta_charset['charset']
            # 如果还是没有，尝试 chardet (需要安装 chardet 库)
            # if not charset:
            #     try:
            #         import chardet
            #         charset = chardet.detect(response.content)['encoding']
            #     except ImportError:
            #         pass # chardet not installed

            # 使用检测到的编码或默认 UTF-8 解码
            response.encoding = charset if charset else 'utf-8'
            logger.debug(f"  -> 使用编码 '{response.encoding}' 解码内容")
            return response.text
        else:
            logger.debug(f"  -> 读取本地文件: {input_path}")
            # 读取本地文件时尝试自动检测编码
            try:
                with open(input_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                logger.warning(f"⚠️ UTF-8解码失败，尝试GBK编码: {input_path}")
                try:
                    with open(input_path, 'r', encoding='gbk') as f:
                        return f.read()
                except Exception as e:
                    logger.error(f"❌ 使用GBK编码读取文件失败: {e}")
                    raise  # 重新抛出异常
