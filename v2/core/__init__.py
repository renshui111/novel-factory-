# core/__init__.py -- 重导出 + logging
import os
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger('novel_factory')
logger.setLevel(logging.INFO)

if not logger.handlers:
    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    try:
        d = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'NovelFactory')
        os.makedirs(d, exist_ok=True)
        fh = RotatingFileHandler(os.path.join(d, 'novel_factory.log'),
                                 maxBytes=2_000_000, backupCount=3, encoding='utf-8')
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass

from .config import *
from .llm import *
from .utils import *
