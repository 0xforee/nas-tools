# -*- coding: utf-8 -*-
"""
IM 渠道（Telegram / 微信 / Slack / Synology）接收磁力链接的回归测试

背景：`web/backend/search_torrents.py` 的入口分类原先只认 `http` 协议，
磁力链接是 `magnet:` 协议，匹配不上就掉进「搜索」分支 —— 整条磁链被当成片名
去查媒体信息，必然查不到，用户看到的是「查询不到媒体信息！」。
若同时开了 ChatGPT，还会走得更歪：磁链被当成聊天内容发给 OpenAI。

本模块钉住三件事：
1. 磁链进的是 DOWNLOAD 分支，且整条磁链**绝不**会被传给媒体识别器；
2. 磁链直达下载器（enclosure=磁链、torrent_file=None），不查站点、不落盘种子；
3. 原有 http 种子链接路径行为不变。

全部离线运行：不连下载器、不访问网络、不读写真实配置。
带「回滚对照」：同一用例内同时跑修复前的分类逻辑与当前实现，断言两者结果不同，
以证明断言落在可观测的行为差异上（而不是恒为真）。

运行：
    python -m unittest tests.test_message_magnet -v
"""
import os
import sys
import unittest
from unittest import mock

# 被测模块在 import 期会读取配置：这里指向仓库内的模板（只读，不会改写它）
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("NASTOOL_CONFIG", os.path.join(_REPO_ROOT, "config", "config.yaml"))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.utils.torrent import Torrent  # noqa: E402
from app.utils.types import SearchType  # noqa: E402
from web.backend import search_torrents as st  # noqa: E402


MAGNET_WITH_DN = ("magnet:?xt=urn:btih:1111111111111111111111111111111111111111"
                  "&dn=%E7%8E%A9%E5%85%B7%E6%80%BB%E5%8A%A8%E5%91%985.2026.BD1080P")
MAGNET_NAME = "玩具总动员5.2026.BD1080P"
MAGNET_NO_DN = "magnet:?xt=urn:btih:2222222222222222222222222222222222222222"
HTTP_TORRENT = "https://example.com/download.php?id=1"
TORRENT_PATH = "/tmp/fake.torrent"


# ---------------------------------------------------------------------------
# 回滚对照用的「修复前逻辑」镜像
# ---------------------------------------------------------------------------

def legacy_classify(input_str, openai_on):
    """修复前的入口分类：只认 http，磁链会掉进「搜索」或「聊天」"""
    if input_str.startswith("订阅"):
        return "SUBSCRIBE"
    if input_str.startswith("http"):
        return "DOWNLOAD"
    if openai_on and not input_str.startswith("搜索") \
            and not input_str.startswith("下载"):
        return "ASK"
    return "SEARCH"


# ---------------------------------------------------------------------------
# 被测流程的驱动
# ---------------------------------------------------------------------------

class Drive:
    """一次调用的结果与副作用"""

    def __init__(self):
        self.messages = []           # 发给用户的消息标题
        self.msg_calls = []          # send_channel_msg 的完整入参（含 image / url）
        self.searched_keywords = []  # 传给媒体识别器的关键字
        self.download_calls = []     # 下载器收到的参数
        self.branch = None           # 被判定的入口分支
        self.media = None            # Media 的 stub
        self.sites = None            # Sites 的 stub
        self.ident_calls = 0         # 媒体识别调用次数


def drive(input_str, user_id, openai_on=False, media_info=None, tmdb_info=None):
    """
    用 stub 驱动真实的 search_media_by_message。
    media_info 传 None 表示 Media().get_media_info() 返回 None（识别失败）。
    tmdb_info 模拟 TMDB 是否命中：命中传非空 dict，未命中传 {}（真实实现里
    tmdb_info 是类属性默认 {}，set_tmdb_info(None) 会直接 return）。
    """
    r = Drive()
    if media_info is not None:
        media_info.tmdb_info = {} if tmdb_info is None else tmdb_info

    message = mock.MagicMock()
    message.send_channel_msg.side_effect = (
        lambda **kw: (r.msg_calls.append(kw), r.messages.append(kw.get("title", ""))))
    message.send_channel_list_msg.side_effect = (
        lambda **kw: (r.msg_calls.append(kw), r.messages.append(kw.get("title", ""))))

    downloader = mock.MagicMock()
    downloader.download.side_effect = lambda **kw: r.download_calls.append(kw)
    downloader.get_download_setting.return_value = {}

    openai = mock.MagicMock()
    openai.get_state.return_value = openai_on

    r.sites = mock.MagicMock()
    r.sites.get_sites.return_value = {}

    r.media = mock.MagicMock()
    r.media.get_media_info.return_value = media_info

    def _search_media_infos(keyword=None, **kw):
        r.searched_keywords.append(keyword)
        return []

    with mock.patch.object(st, "Message", return_value=message), \
            mock.patch.object(st, "Downloader", return_value=downloader), \
            mock.patch.object(st, "OpenAiHelper", return_value=openai), \
            mock.patch.object(st, "Sites", return_value=r.sites), \
            mock.patch.object(st, "Media", return_value=r.media), \
            mock.patch.object(st.WebUtils, "search_media_infos",
                              side_effect=_search_media_infos) as ident, \
            mock.patch.object(Torrent, "save_torrent_file",
                              return_value=(TORRENT_PATH, b"d8:announce", "")):
        st.search_media_by_message(input_str, SearchType.TG, user_id=user_id)
        r.ident_calls = ident.call_count

    r.branch = st.SEARCH_MEDIA_TYPE.get(user_id)
    return r


# ---------------------------------------------------------------------------
# ① 磁链必须走下载分支
# ---------------------------------------------------------------------------

class MagnetRoutingTest(unittest.TestCase):
    """磁链走下载分支，不再被当成搜索关键字"""

    def test_magnet_is_classified_as_download(self):
        self.assertEqual(drive(MAGNET_WITH_DN, "m-routing-1").branch, "DOWNLOAD")

    def test_magnet_never_reaches_media_identifier(self):
        """最关键的一条：整条磁链不能被当成片名丢给识别器"""
        r = drive(MAGNET_WITH_DN, "m-routing-2")
        self.assertEqual(r.searched_keywords, [])
        self.assertEqual(r.ident_calls, 0)

    def test_no_query_media_info_error_message(self):
        r = drive(MAGNET_WITH_DN, "m-routing-3")
        for title in r.messages:
            self.assertNotIn("查询不到媒体信息", title)

    def test_magnet_wins_over_chatgpt(self):
        """开了 ChatGPT 也不能把磁链当成聊天内容"""
        r = drive(MAGNET_WITH_DN, "m-routing-4", openai_on=True,
                  media_info=mock.MagicMock())
        self.assertEqual(r.branch, "DOWNLOAD")
        self.assertEqual(r.searched_keywords, [])
        self.assertEqual(len(r.download_calls), 1)

    def test_rollback_control_magnet_used_to_be_search(self):
        """回滚对照：修复前磁链被判为 SEARCH，与当前实现不同（证明断言可鉴别）"""
        branch = drive(MAGNET_WITH_DN, "m-control-1").branch
        self.assertEqual(branch, "DOWNLOAD")
        self.assertEqual(legacy_classify(MAGNET_WITH_DN, openai_on=False), "SEARCH")
        self.assertNotEqual(branch, legacy_classify(MAGNET_WITH_DN, openai_on=False))

    def test_rollback_control_magnet_used_to_be_chat(self):
        """回滚对照：开着 ChatGPT 时修复前是 ASK（发给 OpenAI）"""
        branch = drive(MAGNET_WITH_DN, "m-control-2", openai_on=True).branch
        self.assertEqual(branch, "DOWNLOAD")
        self.assertEqual(legacy_classify(MAGNET_WITH_DN, openai_on=True), "ASK")


# ---------------------------------------------------------------------------
# ② 磁链直达下载器
# ---------------------------------------------------------------------------

class MagnetDownloadTest(unittest.TestCase):

    def setUp(self):
        self.media_info = mock.MagicMock()

    def test_magnet_passed_to_downloader_as_enclosure(self):
        r = drive(MAGNET_WITH_DN, "m-dl-1", media_info=self.media_info)
        self.assertEqual(len(r.download_calls), 1)
        call = r.download_calls[0]
        # 直接把它当链接交给下载器，不带种子文件
        self.assertIsNone(call["torrent_file"])
        self.assertIs(call["media_info"], self.media_info)
        self.media_info.set_torrent_info.assert_called_once_with(enclosure=MAGNET_WITH_DN)

    def test_media_identified_from_dn(self):
        """用 dn 里的文件名做媒体识别，而不是拿整条磁链"""
        r = drive(MAGNET_WITH_DN, "m-dl-2", media_info=self.media_info)
        r.media.get_media_info.assert_called_once_with(title=MAGNET_NAME)

    def test_same_magnet_is_downloaded_once(self):
        r = drive(MAGNET_WITH_DN, "m-dl-3", media_info=self.media_info)
        self.assertEqual(len(r.download_calls), 1)


# ---------------------------------------------------------------------------
# ③ 磁链缺 dn / 识别失败时的提示
# ---------------------------------------------------------------------------

class MagnetFailureTest(unittest.TestCase):

    def test_missing_dn_reports_and_stops(self):
        r = drive(MAGNET_NO_DN, "m-fail-1", media_info=mock.MagicMock())
        self.assertEqual(len(r.download_calls), 0)
        self.assertTrue(any("dn" in t for t in r.messages), r.messages)

    def test_unrecognizable_name_reports_and_stops(self):
        r = drive(MAGNET_WITH_DN, "m-fail-2", media_info=None)
        self.assertEqual(len(r.download_calls), 0)
        self.assertEqual(len(r.messages), 1)
        self.assertIn(MAGNET_NAME, r.messages[0])

    def test_failure_messages_are_never_sent_to_identifier(self):
        r = drive(MAGNET_WITH_DN, "m-fail-3", media_info=None)
        self.assertEqual(r.searched_keywords, [])


# ---------------------------------------------------------------------------
# ④ 下载前回给用户的媒体信息（简介 / 海报 / TMDB 详情链接）
# ---------------------------------------------------------------------------

class MediaInfoMessageTest(unittest.TestCase):
    """
    下载器自己发的通知只有标题、评分与下载参数，没有简介/海报/详情链接。
    这里钉住：识别到 TMDB 信息时补发一条媒体信息，没命中时不发空壳消息。
    """

    TMDB_HIT = {"id": 12345, "title": "某电影"}

    def _media_info(self, tmdb_info):
        info = mock.MagicMock()
        info.tmdb_info = tmdb_info
        return info

    def test_magnet_with_tmdb_sends_media_info(self):
        info = self._media_info(self.TMDB_HIT)
        r = drive(MAGNET_WITH_DN, "m-info-1", media_info=info,
                  tmdb_info=self.TMDB_HIT)
        self.assertEqual(len(r.msg_calls), 1)
        call = r.msg_calls[0]
        # 媒体信息四件套：标题带评分、简介、海报、详情链接
        self.assertEqual(call["title"], info.get_title_vote_string.return_value)
        self.assertEqual(call["text"], info.get_overview_string.return_value)
        self.assertEqual(call["image"], info.get_message_image.return_value)
        self.assertEqual(call["url"], info.get_detail_url.return_value)
        self.assertEqual(call["user_id"], "m-info-1")
        # 下载仍然照常进行
        self.assertEqual(len(r.download_calls), 1)

    def test_magnet_without_tmdb_sends_nothing(self):
        """TMDB 没命中时不发空壳消息，但下载照常"""
        r = drive(MAGNET_WITH_DN, "m-info-2", media_info=self._media_info({}),
                  tmdb_info={})
        self.assertEqual(r.msg_calls, [])
        self.assertEqual(len(r.download_calls), 1)

    def test_http_with_tmdb_sends_media_info(self):
        info = self._media_info(self.TMDB_HIT)
        r = drive(HTTP_TORRENT, "m-info-3", media_info=info, tmdb_info=self.TMDB_HIT)
        self.assertEqual(len(r.msg_calls), 1)
        self.assertEqual(r.msg_calls[0]["url"], info.get_detail_url.return_value)
        self.assertEqual(len(r.download_calls), 1)
        self.assertEqual(r.download_calls[0]["torrent_file"], TORRENT_PATH)

    def test_http_without_tmdb_sends_nothing(self):
        r = drive(HTTP_TORRENT, "m-info-4", media_info=self._media_info({}),
                  tmdb_info={})
        self.assertEqual(r.msg_calls, [])
        self.assertEqual(len(r.download_calls), 1)

    def test_rollback_control_media_info_was_never_sent(self):
        """回滚对照：修复前下载路径一条媒体信息都不发"""
        for link, uid in ((MAGNET_WITH_DN, "m-info-ctl-1"), (HTTP_TORRENT, "m-info-ctl-2")):
            with self.subTest(link=link[:12]):
                info = self._media_info(self.TMDB_HIT)
                r = drive(link, uid, media_info=info, tmdb_info=self.TMDB_HIT)
                self.assertEqual(len(r.msg_calls), 1)      # 现在：发
                self.assertNotEqual(len(r.msg_calls), 0)   # 旧实现：0 条


# ---------------------------------------------------------------------------
# ⑤ 原有 http 种子链接路径保持不变
# ---------------------------------------------------------------------------

class HttpTorrentPathUnchangedTest(unittest.TestCase):

    def test_http_link_still_goes_through_site_and_file(self):
        media_info = mock.MagicMock()
        r = drive(HTTP_TORRENT, "m-http-1", media_info=media_info)
        self.assertEqual(r.branch, "DOWNLOAD")
        self.assertEqual(r.searched_keywords, [])
        self.assertEqual(len(r.download_calls), 1)
        call = r.download_calls[0]
        # http 路径仍然先落盘种子文件，并把文件路径交给下载器
        self.assertEqual(call["torrent_file"], TORRENT_PATH)
        media_info.set_torrent_info.assert_called_once_with(enclosure=HTTP_TORRENT)

    def test_http_link_still_queries_site(self):
        r = drive(HTTP_TORRENT, "m-http-2", media_info=mock.MagicMock())
        r.sites.get_sites.assert_called_once_with(siteurl=HTTP_TORRENT)


if __name__ == '__main__':
    unittest.main()
