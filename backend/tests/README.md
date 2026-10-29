# 服务端测试

存放服务端自动化测试，按接口、核心规则、数据库和集成场景分类。测试用例应关联需求编号并保存实际结果。

## 快速开始

在 `backend/` 目录下执行（使用仓库内已有的虚拟环境）：

```sh
# Windows
.venv\Scripts\python -m pytest

# macOS / Linux
.venv/bin/python -m pytest
```

常用筛选方式：

```sh
.venv\Scripts\python -m pytest tests/api                    # 只跑接口层
.venv\Scripts\python -m pytest tests/modules -q             # 只跑业务服务层
.venv\Scripts\python -m pytest -k "claim and 403"           # 按名称筛选
.venv\Scripts\python -m pytest tests/api/test_items.py -v   # 单文件 + 详细输出
```

如果本机安装了 [uv](https://docs.astral.sh/uv/)，也可以用 `uv run pytest`，效果相同。

pytest 配置写在 `backend/pyproject.toml` 的 `[tool.pytest.ini_options]`，
已设置 `testpaths=tests` 与 `pythonpath=.`，因此在 `backend/` 下直接执行即可，
不需要额外设置 `PYTHONPATH`，也不需要把本项目安装为包。
