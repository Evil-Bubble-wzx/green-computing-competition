"""
测试配置 - pytest fixtures 和共享工具
"""

import sys
from pathlib import Path

import pytest

# 确保 src 在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session")
def project_root():
    """项目根目录"""
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def docx_dir(project_root):
    """测试数据目录"""
    return project_root / "docx"


@pytest.fixture(scope="session")
def settings():
    """加载测试配置"""
    from src.core.settings import load_settings

    config_path = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
    return load_settings(config_path)
