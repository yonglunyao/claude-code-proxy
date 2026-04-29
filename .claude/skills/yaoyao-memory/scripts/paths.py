# -*- coding: utf-8 -*-
"""路径配置 - yaoyao-memory-dev"""
from pathlib import Path
import os

# Skill 目录
SKILL_DIR = Path(__file__).parent.parent

# 向量数据库
VECTORS_DB = os.environ.get("VECTORS_DB", str(Path.home() / ".openclaw" / "workspace" / "memory" / "vectors.db"))

# SQLite vec 扩展
VEC_EXT = os.environ.get("VEC_EXT", str(Path.home() / ".openclaw" / "extensions" / "memory-tencentdb" / "node_modules" / "sqlite-vec-linux-x64" / "vec0"))
