# -*- coding: utf-8 -*-
"""
qBittorrent 5.x 兼容性回归测试

覆盖本 fork 相对上游额外做的 qB 兼容修复。上游 0xforee 在 2026-07-14 用
f59f8e2（撤回 qB 5.2 兼容修复）与 c2063e1（撤回 qbittorrent-api 2026.6.0 升级）
revert 过同类改动，本批修复是在 revert 之后重做的 —— 这组用例的作用就是让
「修复被改回去」这件事能被 CI 直接抓到，而不是等用户遇到故障才发现。

全部离线运行：只构造 stub 对象驱动被测方法，不连接真实下载器、不访问网络。
每个用例都带「回滚对照」：同一用例内同时跑新实现与修复前的逻辑，并断言两者结果
不同，用以证明断言落在可观测的行为差异上（而不是恒为真）。

运行：
    python -m unittest tests.test_qbittorrent_compat -v
"""
import inspect
import json
import os
import sys
import unittest
from unittest import mock

# 被测模块在 import 期会读取配置：这里指向仓库内的模板（只读，不会改写它）
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("NASTOOL_CONFIG", os.path.join(_REPO_ROOT, "config", "config.yaml"))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import qbittorrentapi  # noqa: E402
import web.action as web_action  # noqa: E402
from web.action import WebAction  # noqa: E402

from app.downloader.client.qbittorrent import (  # noqa: E402
    QB_PAUSED_DOWNLOAD_STATES,
    QB_PAUSED_UPLOAD_STATES,
    Qbittorrent,
)
from app.plugins.modules.iyuuautoseed import IYUUAutoSeed  # noqa: E402
from app.plugins.modules.torrenttransfer import TorrentTransfer  # noqa: E402
from app.utils.torrent import Torrent  # noqa: E402
from app.utils.types import DownloaderType  # noqa: E402


# ---------------------------------------------------------------------------
# 回滚对照用的「修复前逻辑」镜像
# ---------------------------------------------------------------------------

def legacy_is_magnet(link):
    """修复前的磁链判定：写死 xt 必须紧跟 ? 且为 urn:btih:"""
    return link.lower().startswith("magnet:?xt=urn:btih:")


def legacy_parse_add_response(response):
    """修复前的添加种子结果判定"""
    return str(response).find("Ok") != -1


def legacy_can_seeding(state):
    """修复前的插件判定：只认 qB 4.x 的 pausedUP"""
    return state == "pausedUP"


def legacy_download_torrent_judge(download_result):
    """修复前 __download_torrent 的判据：直接看第二个返回值（种子ID）"""
    _, ret, _, ret_msg = download_result
    if not ret:
        return {"code": -1, "msg": ret_msg or "添加下载失败"}
    return {"code": 0, "msg": "添加下载完成！"}


class _StubQbc:
    """最小 qbittorrent-api Client 替身：只记录被调用的方法，不做任何 IO"""

    def __init__(self, torrents=None):
        self.torrents = list(torrents or [])
        self.torrents_info_calls = []
        self.deleted_tags = []

    def torrents_info(self, **kwargs):
        self.torrents_info_calls.append(kwargs)
        return list(self.torrents)

    def torrents_delete_tags(self, **kwargs):
        self.deleted_tags.append(kwargs)

    def torrents_remove_tags(self, **kwargs):
        # 该方法会把标签定义留在下载器里，实现中不应使用它
        raise AssertionError("remove_torrents_tag 不应调用 torrents_remove_tags")


def _new_client(stub):
    """绕过 __init__（不建连接）构造客户端实例"""
    client = object.__new__(Qbittorrent)
    client.qbc = stub
    return client


# ---------------------------------------------------------------------------
# ① 磁链判定
# ---------------------------------------------------------------------------

class TorrentIsMagnetTest(unittest.TestCase):
    """磁链判定只认 magnet: 协议，不约束参数顺序与 xt 类型（348ae7d 的配套修复）"""

    # dn/tr 在 xt 之前、BT v2 用 urn:btmh: —— 这些都是合法磁链，
    # 修复前的写死前缀判定会把它们漏掉，导致 WEB 添加下载误报「未匹配到站点」
    NON_CANONICAL_MAGNETS = (
        "magnet:?dn=Movie.2024.1080p&xt=urn:btih:ABCDEF0123",
        "magnet:?tr=https%3A%2F%2Ftracker.example&xt=urn:btih:ABCDEF0123",
        "magnet:?xt=urn:btmh:1220abcdef&dn=Movie",  # BT v2 (SHA-256)
        "magnet:?dn=Movie",                          # 无 xt
    )

    def test_canonical_magnet(self):
        self.assertTrue(Torrent.is_magnet("magnet:?xt=urn:btih:ABCDEF&dn=Movie"))

    def test_scheme_is_case_insensitive(self):
        self.assertTrue(Torrent.is_magnet("MAGNET:?xt=urn:btih:ABCDEF"))

    def test_non_magnet_inputs(self):
        for link in ("http://example.com/a.torrent", "https://x/y", "", None, "not a link"):
            self.assertFalse(Torrent.is_magnet(link), link)

    def test_non_canonical_shape_is_recognized(self):
        """回滚对照：这些形态旧判定为假，新判定为真"""
        for link in self.NON_CANONICAL_MAGNETS:
            with self.subTest(link=link):
                self.assertTrue(Torrent.is_magnet(link))
                self.assertFalse(legacy_is_magnet(link))

    def test_get_magnet_name_reads_dn(self):
        self.assertEqual(
            Torrent.get_magnet_name("magnet:?xt=urn:btih:ABCDEF&dn=Movie.2024.1080p"),
            "Movie.2024.1080p",
        )
        # dn 在 xt 之前同样要能取到（旧实现连带提取都依赖同一个前缀判定）
        self.assertEqual(
            Torrent.get_magnet_name("magnet:?dn=Movie&xt=urn:btih:ABCDEF"),
            "Movie",
        )

    def test_get_magnet_name_without_dn(self):
        self.assertIsNone(Torrent.get_magnet_name("magnet:?xt=urn:btih:ABCDEF"))
        self.assertIsNone(Torrent.get_magnet_name("http://example.com/a.torrent"))
        self.assertIsNone(Torrent.get_magnet_name(None))


class MagnetJudgementSharedTest(unittest.TestCase):
    """下载器与 WEB 入口必须共用同一个判定，避免再次各写一份"""

    def test_downloader_delegates_to_torrent_is_magnet(self):
        import app.downloader.downloader as downloader_module

        src = inspect.getsource(downloader_module)
        self.assertIn("Torrent.is_magnet(", src)
        self.assertNotIn('startswith("magnet:")', src)

    def test_is_magnet_is_the_single_place_holding_the_prefix(self):
        """磁链前缀判断只应出现在 is_magnet 里，别处再写内联判断就是重复"""
        import app.utils.torrent as torrent_module

        src = inspect.getsource(torrent_module)
        self.assertNotIn('startswith("magnet:?xt=urn:btih:")', src)
        self.assertEqual(src.count('startswith("magnet:")'), 1)


# ---------------------------------------------------------------------------
# ② /torrents/add 返回体解析（qB 5.2 起为 JSON）
# ---------------------------------------------------------------------------

class AddTorrentResponseTest(unittest.TestCase):
    """7787fdd：qB 5.2.0（WebAPI 2.14.0）起 /torrents/add 返回 JSON 而非 "Ok." """

    @classmethod
    def setUpClass(cls):
        cls.parse = _new_client(_StubQbc())._Qbittorrent__parse_add_torrent_response

    def test_plain_text_success(self):
        self.assertTrue(self.parse("Ok."))

    def test_plain_text_failure(self):
        self.assertFalse(self.parse("Fails."))

    def test_json_object(self):
        """新版库（2026.6.0）会 resp.json()，返回已解析的映射"""
        self.assertTrue(self.parse({
            "added_torrent_ids": ["a1"], "failure_count": 0,
            "pending_count": 0, "success_count": 1,
        }))

    def test_json_string(self):
        """旧版库会把 JSON 原样当字符串返回"""
        self.assertTrue(self.parse(json.dumps({
            "added_torrent_ids": ["a1"], "failure_count": 0,
            "pending_count": 0, "success_count": 1,
        })))

    def test_magnet_pending_only(self):
        """磁链添加时只有 pending_count"""
        self.assertTrue(self.parse({
            "added_torrent_ids": [], "failure_count": 0,
            "pending_count": 1, "success_count": 0,
        }))

    def test_all_failed(self):
        self.assertFalse(self.parse({
            "added_torrent_ids": [], "failure_count": 1,
            "pending_count": 0, "success_count": 0,
        }))

    def test_falsy_inputs(self):
        for response in (None, "", 0, "Internal Server Error"):
            self.assertFalse(self.parse(response), repr(response))

    def test_legacy_judge_misreports_json_success(self):
        """回滚对照：修复前只要响应不是纯文本 "Ok." 就判失败"""
        success = {"added_torrent_ids": ["a1"], "failure_count": 0,
                   "pending_count": 0, "success_count": 1}
        self.assertTrue(self.parse(success))
        self.assertFalse(legacy_parse_add_response(success))
        self.assertFalse(legacy_parse_add_response(json.dumps(success)))
        # 纯文本场景两者一致，说明差异只来自 JSON
        self.assertEqual(self.parse("Ok."), legacy_parse_add_response("Ok."))


class StatusFilterTest(unittest.TestCase):
    """d870150：qbittorrent-api 2026.x 的 torrents_info 只接受字符串 status_filter"""

    def test_list_is_normalized(self):
        stub = _StubQbc()
        client = _new_client(stub)
        client.get_torrents(status=["completed"])
        self.assertEqual(stub.torrents_info_calls[-1]["status_filter"], "completed")

    def test_multiple_statuses_joined(self):
        stub = _StubQbc()
        client = _new_client(stub)
        client.get_torrents(status=["completed", "downloading"])
        self.assertEqual(stub.torrents_info_calls[-1]["status_filter"], "completed|downloading")

    def test_real_library_rejects_list(self):
        """回滚对照：把列表原样交给真实库会抛 TypeError（即修复前的情形）"""
        client = qbittorrentapi.Client(host="127.0.0.1", port=8080)
        # 只走参数处理，不发请求
        client._post_cast = lambda *args, **kwargs: []
        self.assertEqual(client.torrents_info(status_filter="completed"), [])
        with self.assertRaises(TypeError):
            client.torrents_info(status_filter=["completed"])


# ---------------------------------------------------------------------------
# ③ 暂停状态改名
# ---------------------------------------------------------------------------

class PausedStatesTest(unittest.TestCase):
    """6356c4e：qB 5.0 起暂停状态由 pausedDL/pausedUP 改名为 stoppedDL/stoppedUP"""

    def test_constants_cover_both_schemes(self):
        self.assertIn("pausedDL", QB_PAUSED_DOWNLOAD_STATES)     # qB 4.x
        self.assertIn("stoppedDL", QB_PAUSED_DOWNLOAD_STATES)    # qB 5.x
        self.assertIn("pausedUP", QB_PAUSED_UPLOAD_STATES)
        self.assertIn("stoppedUP", QB_PAUSED_UPLOAD_STATES)

    def test_iyuu_can_seeding(self):
        can_seeding = IYUUAutoSeed._IYUUAutoSeed__can_seeding
        self.assertTrue(can_seeding({"state": "pausedUP"}, DownloaderType.QB))
        self.assertTrue(can_seeding({"state": "stoppedUP"}, DownloaderType.QB))
        self.assertFalse(can_seeding({"state": "downloading"}, DownloaderType.QB))

    def test_torrenttransfer_can_seeding(self):
        can_seeding = TorrentTransfer._TorrentTransfer__can_seeding
        self.assertTrue(can_seeding({"state": "stoppedUP", "tracker": "tr"}, DownloaderType.QB))
        self.assertFalse(can_seeding({"state": "stoppedUP"}, DownloaderType.QB))
        self.assertFalse(can_seeding({"state": "downloading", "tracker": "tr"}, DownloaderType.QB))

    def test_legacy_judge_misses_qb5_state(self):
        """回滚对照：修复前的判定对 qB 5.x 实测返回的 stoppedUP 恒为假"""
        self.assertFalse(legacy_can_seeding("stoppedUP"))
        self.assertTrue(IYUUAutoSeed._IYUUAutoSeed__can_seeding(
            {"state": "stoppedUP"}, DownloaderType.QB))


# ---------------------------------------------------------------------------
# ④ 临时标签的生命周期
# ---------------------------------------------------------------------------

class TagLifecycleTest(unittest.TestCase):
    """89001df / 8c63ea2：临时标签必须按「删除标签定义」清理，且无论成败都要清"""

    def test_remove_torrents_tag_sends_only_tag(self):
        stub = _StubQbc()
        client = _new_client(stub)
        self.assertTrue(client.remove_torrents_tag("NTabcde"))
        self.assertEqual(stub.deleted_tags, [{"tags": "NTabcde"}])

    def test_tag_is_cleaned_when_no_torrent_matched(self):
        stub = _StubQbc(torrents=[])  # 永远匹配不到种子
        client = _new_client(stub)
        with mock.patch("time.sleep"):  # 跳过 5 次 × 5 秒重试
            torrent_id = client.get_torrent_id_by_tag("NTabcde")
        self.assertIsNone(torrent_id)
        self.assertEqual(stub.deleted_tags, [{"tags": "NTabcde"}])

    def test_tag_is_cleaned_when_torrent_matched(self):
        stub = _StubQbc(torrents=[{"hash": "h1", "tags": ["NTabcde"]}])
        client = _new_client(stub)
        with mock.patch("time.sleep"):
            torrent_id = client.get_torrent_id_by_tag("NTabcde")
        self.assertEqual(torrent_id, "h1")
        self.assertEqual(stub.deleted_tags, [{"tags": "NTabcde"}])

    def test_legacy_cleanup_path_would_leak_tag(self):
        """回滚对照：修复前只在匹配到种子时才清理，匹配失败会残留标签定义"""
        # 把 8c63ea2 之前的调用时机在测试内还原一遍，用于对照
        legacy_stub = _StubQbc(torrents=[])
        legacy_torrent_id = None
        for _ in range(5):
            matched = legacy_stub.torrents_info() or []
            legacy_torrent_id = matched[0].get("hash") if matched else None
            if legacy_torrent_id is None:
                continue
            else:
                legacy_stub.torrents_delete_tags(tags="NTabcde")
                break
        self.assertIsNone(legacy_torrent_id)
        self.assertEqual(legacy_stub.deleted_tags, [])  # 旧行为确实残留标签定义

        # 新行为：无论是否匹配到都清理
        stub = _StubQbc(torrents=[])
        client = _new_client(stub)
        with mock.patch("time.sleep"):
            client.get_torrent_id_by_tag("NTabcde")
        self.assertEqual(stub.deleted_tags, [{"tags": "NTabcde"}])


# ---------------------------------------------------------------------------
# ⑤ 添加下载的成败判据
# ---------------------------------------------------------------------------

class DownloadResultJudgeTest(unittest.TestCase):
    """
    Downloader().download() 的第二个返回值是种子 ID，不是成功标志：
    QB 分支下它由 get_torrent_id_by_tag() 取得，匹配不到时就是 None。
    因此 web 层必须用 ret_msg 判成败，否则会把「已添加但取不到ID」误报为失败。
    """

    FILENAME = "sample.torrent"

    def _invoke_download_torrent(self, download_result):
        """用 stub 驱动 __download_torrent 的「上传种子文件」分支"""
        with mock.patch.object(web_action, "Config") as config, \
                mock.patch.object(web_action, "Media") as media, \
                mock.patch.object(web_action, "Downloader") as downloader, \
                mock.patch.object(web_action, "current_user"):
            config.return_value.get_temp_path.return_value = _REPO_ROOT
            media.return_value.get_media_info.return_value = media.return_value
            downloader.return_value.download.return_value = download_result
            return WebAction._WebAction__download_torrent({
                "files": [{"upload": {"filename": self.FILENAME}}],
                "dl_dir": "",
                "dl_setting": "",
            })

    def test_real_failure_is_reported(self):
        """下载器失效等真实失败：ret_msg 非空，必须报错并透出原因"""
        msg = "下载设置 默认 所选下载器失效"
        ret = self._invoke_download_torrent((None, None, None, msg))
        self.assertEqual(ret["code"], -1)
        self.assertEqual(ret["msg"], msg)

    def test_success_without_torrent_id_is_success(self):
        """添加成功但 25 秒内未取到种子 ID：仍是成功，不能误报失败"""
        ret = self._invoke_download_torrent(("qbittorrent", None, None, ""))
        self.assertEqual(ret["code"], 0)

    def test_success_with_torrent_id(self):
        ret = self._invoke_download_torrent(("qbittorrent", "h1", "/downloads", ""))
        self.assertEqual(ret["code"], 0)

    def test_legacy_judge_misreports_success_as_failure(self):
        """回滚对照：修复前的判据会把「成功但取不到ID」判成失败"""
        result = ("qbittorrent", None, None, "")
        self.assertEqual(self._invoke_download_torrent(result)["code"], 0)
        self.assertEqual(legacy_download_torrent_judge(result)["code"], -1)

    def test_entrypoints_judge_by_ret_msg(self):
        """三个入口都必须以 ret_msg 为判据（防止回退成 `if not ret`）"""
        for name in ("_WebAction__download",
                     "_WebAction__download_link",
                     "_WebAction__download_torrent"):
            with self.subTest(entrypoint=name):
                src = inspect.getsource(getattr(WebAction, name))
                self.assertIn("if ret_msg:", src)
                self.assertNotIn("if not ret:", src)


if __name__ == '__main__':
    unittest.main(verbosity=2)
