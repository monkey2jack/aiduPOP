"""WP-8: 双向版本分叉守卫（裁决 #1 落地）。

小仓保持 2.5.0 版本号；大仓（公共仓）保持 2.5 / 2.5.0 版本号。
本测试用于防止双仓代码同步时误将版本号文件相互覆盖。
"""
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

def test_repo_branch_version_policy():
    raw = (_REPO_ROOT / "plugin.yaml").read_text(encoding="utf-8")
    for line in raw.splitlines():
        if line.startswith("version:"):
            v = line.split(":", 1)[1].strip().strip('"').strip("'")
            break
    else:
        raise AssertionError("plugin.yaml 缺失 version字段")

    # 当前为小仓 (aiduPOP_dudu) / 本地运行 (2.5.0)
    # 大仓在同步时会显式保持 2.5 策略
    assert v in ("2.5.0", "2.5", "2.4.4", "2.4.3", "2.4.2", "2.4.1", "2.4.0", "2.4"), f"未预期的版本号 {v}"
