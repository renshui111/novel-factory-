# core/__init__.py — 重导出 + logging 初始化

import logging
logger = logging.getLogger('novel_factory')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

from .config import *
from .llm import *
from .utils import *