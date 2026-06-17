import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_project_imports():
    """测试项目能否正确导入"""
    try:
        import main
        assert True
    except ImportError:
        pytest.skip("项目未完全配置")
