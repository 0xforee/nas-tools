import os
import sys
import unittest

# 被测模块在 import 期会读取配置：这里指向仓库内的模板（只读，不会改写它）
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("NASTOOL_CONFIG", os.path.join(_REPO_ROOT, "config", "config.yaml"))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tests.test_metainfo import MetaInfoTest  # noqa: E402
from tests.test_qbittorrent_compat import (  # noqa: E402
    AddTorrentResponseTest,
    DownloadResultJudgeTest,
    MagnetJudgementSharedTest,
    PausedStatesTest,
    StatusFilterTest,
    TagLifecycleTest,
    TorrentIsMagnetTest,
)

if __name__ == '__main__':
    suite = unittest.TestSuite()
    # 测试名称识别
    suite.addTest(MetaInfoTest('test_metainfo'))

    # qBittorrent 5.x 兼容性回归用例（上游曾 revert 过同类修复，详见模块 docstring）
    loader = unittest.TestLoader()
    for test_case in (TorrentIsMagnetTest,
                      MagnetJudgementSharedTest,
                      AddTorrentResponseTest,
                      StatusFilterTest,
                      PausedStatesTest,
                      TagLifecycleTest,
                      DownloadResultJudgeTest):
        suite.addTest(loader.loadTestsFromTestCase(test_case))

    # 运行测试
    runner = unittest.TextTestRunner()
    runner.run(suite)
