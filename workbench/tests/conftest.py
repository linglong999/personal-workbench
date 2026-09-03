"""测试全局夹具：usage SQLite 库指向各自 tmp_path——隔离 .data/usage.db 真文件。"""

import pytest

from workbench import usage


@pytest.fixture(autouse=True)
def _usage_tmp_db(tmp_path):
    usage.set_db(str(tmp_path / "usage.db"))
    yield
