import requests

import log
from app.utils import RequestUtils, MteamUtils
from config import Config


class MTeamSpider(object):
    _appid = "nastool"
    _req = None
    _token = None
    _api_url = "%s/api/torrent/search"
    _pageurl = "%sdetail/%s"

    def __init__(self, indexer):
        if indexer:
            self._indexerid = indexer.id
            self._domain = indexer.domain
            self._name = indexer.name
            self._proxy = Config().get_proxies() if indexer.proxy else None
            self._cookie = indexer.cookie
            self._ua = indexer.ua
        self._api_url = self._api_url % MteamUtils.get_api_url(self._domain)
        self.init_config()

    def init_config(self):
        session = requests.session()
        self._req = MteamUtils.buildRequestUtils(proxies=self._proxy, session=session, content_type="application/json",
            accept_type="application/json", api_key=MteamUtils.get_api_key(self._domain), headers=self._ua, timeout=10)

    def get_discount(self, discount):
        if discount == "PERCENT_50":
            return 1.0, 0.5
        elif discount == "NORMAL":
            return 1.0, 1.0
        elif discount == "PERCENT_70":
            return 1.0, 0.7
        elif discount == "FREE":
            return 1.0, 0.0
        elif discount == "_2X_FREE":
            return 2.0, 0.0
        elif discount == "_2X":
            return 2.0, 1.0
        elif discount == "_2X_PERCENT_50":
            return 2.0, 0.5

    def inner_search(self, keyword, page=None):
        if page:
            page = int(page) + 1
        else:
            page = 1

        param = {
            "categories":[],
            "keyword": keyword,
            "mode":"normal",
            "pageNumber": page,
            "pageSize":100,
            "visible":1
        }
        # if imdb_id:
        #     params['search_imdb'] = imdb_id
        # else:
        #     params['search_string'] = keyword
        res = self._req.post_res(url=self._api_url, json=param)
        torrents = []
        if res and res.status_code == 200:
            results = res.json().get('data') or {}
            # TODO 遍历多个页面获取数据
            totalPages = results.get("totalPages")
            total = results.get("total")
            curData = results.get('data') or []

            for result in curData:
                status = result.get("status")
                up_discount, down_discount = self.get_discount(status.get('discount'))
                torrent = {'indexer': self._indexerid,
                           'title': result.get('name'),
                           'description': result.get('smallDescr'),
                           # enlosure 给 pageurl，后续下载种子的时候，从接口中解析，这里只是为了跳过中间的检验流程
                           'enclosure': self._pageurl % (self._domain, result.get('id')),
                           'size': result.get('size'),
                           'seeders': status.get('seeders'),
                           'peers': status.get('leechers'),
                           # 'freeleech': result.get('discount'),
                           'downloadvolumefactor': down_discount,
                           'uploadvolumefactor': up_discount,
                           'page_url': self._pageurl % (self._domain, result.get('id')),
                           'imdbid': result.get('episode_info').get('imdb') if result.get('episode_info') else ''}
                torrents.append(torrent)
        elif res is not None:
            log.warn(f"【INDEXER】{self._name} 搜索失败，错误码：{res.status_code}")
            return True, []
        else:
            log.warn(f"【INDEXER】{self._name} 搜索失败，无法获取请求结果")
            return True, []
        return False, torrents

    def search(self, keyword, page=None):
        if not keyword:
            return True, []

        return self.inner_search(keyword, page)
