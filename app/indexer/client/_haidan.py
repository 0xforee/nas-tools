from pyquery import PyQuery
from app.utils.exception_utils import ExceptionUtils
import copy
import log
from jinja2 import Template

from app.indexer.client._spider import TorrentSpider


class HaiDanSpider(TorrentSpider):

    def parse(self, request, response):
        """
        解析整个页面
        """
        try:
            # 获取站点文本
            html_text = response.extract()
            html_text = self.clean_all_sites_free(html_text)
            if not html_text:
                self.is_error = True
                self.is_complete = True
                return
            # 解析站点文本对象
            html_doc = PyQuery(html_text)
            # 种子筛选器
            torrents_selector = self.list.get('selector', '')
            # 遍历种子html列表
            for torn in html_doc(torrents_selector):
                group = PyQuery(torn)
                for torrent in group('div.torrent_wrap'):
                    # log.debug(f"[haidan] {torrent}")
                    torrent_query = PyQuery(torrent)
                    torrent_info = self.Getinfo(torrent_query)
                    # use group name + torrent name override
                    self.Gettitle_with_group(group, torrent_query)
                    self.torrents_info_array.append(copy.deepcopy(torrent_info))
                    if len(self.torrents_info_array) >= int(self.result_num):
                        break

        except Exception as err:
            self.is_error = True
            ExceptionUtils.exception_traceback(err)
            log.warn(f"【Spider】错误：{self.indexername} {str(err)}")
        finally:
            self.is_complete = True