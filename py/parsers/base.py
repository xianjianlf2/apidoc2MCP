#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基础API文档解析器类
定义通用解析接口
"""

from abc import ABC, abstractmethod

class BaseParser(ABC):
    """
    基础API文档解析器抽象类
    所有特定格式的解析器都应继承此类
    """
    
    @abstractmethod
    def parse(self, input_path):
        """
        解析API文档
        
        Args:
            input_path: 文档路径，可以是URL或文件路径
        
        Returns:
            解析后的API数据
        """
        pass
    
    def is_url(self, input_path):
        """
        判断输入是否为URL
        
        Args:
            input_path: 输入路径
        
        Returns:
            是否为URL
        """
        return input_path.startswith('http://') or input_path.startswith('https://')
    
    def load_content(self, input_path):
        """
        加载文档内容
        
        Args:
            input_path: 文档路径，可以是URL或文件路径
        
        Returns:
            文档内容
        """
        if self.is_url(input_path):
            # 加载URL内容
            import requests
            response = requests.get(input_path)
            response.raise_for_status()  # 如果请求失败则抛出异常
            return response.text
        else:
            # 加载本地文件内容
            with open(input_path, 'r', encoding='utf-8') as f:
                return f.read() 