# -*- coding: utf-8 -*-
import json
import re

from lxml import etree

import log
from app.sites.siteuserinfo._base import _ISiteUserInfo, SITE_BASE_ORDER
from app.utils import StringUtils
from app.utils.types import SiteSchema
from app.utils import RequestUtils, ExceptionUtils
from app.sites.siteuserinfo.nexus_php import NexusPhpSiteUserInfo

class MteamSiteUserInfo(NexusPhpSiteUserInfo):
    schema = SiteSchema.Mteam
    order = SITE_BASE_ORDER

    @classmethod
    def match(cls, html_text):
        """
        默认使用NexusPhp解析
        :param html_text:
        :return:
        """
        return "M-Team" in html_text

    def _parse_logged_in(self, html_text):
        url = f"{self.site_url}api/member/profile"
        res = RequestUtils(
            headers=self._ua,
            cookies=self._site_cookie,
            timeout=15
        ).post_res(url=url)
        if res and res.status_code == 200:
            user_info = res.json()
            if user_info and user_info.get("data"):
                return True, "连接成功"
        return False, "Cookie已失效"

    def get_user_profile(self):
        url = f"{self.site_url}/api/member/profile"
        res = RequestUtils(
            headers=self._ua,
            cookies=self._site_cookie,
            session=self._session,
            timeout=15
        ).post_res(url=url)
        if res and res.status_code == 200:
            user_info = res.json()
            if user_info and user_info.get("data"):
                return user_info.get("data")
        return None

    def parseSeedingList(self, dataList):
        seeding_info = []
        total_size = 0
        for item in dataList:
            torrent = item.get("torrent")
            size = StringUtils.str_int(torrent.get("size"))
            total_size += size
            seeders = StringUtils.str_int(torrent.get("status").get("seeders"))
            seeding_info.append([seeders, size])

        return total_size, seeding_info

    def parse_seeding(self):
        # get first page
        all_seeding_info = []
        data = self.getSeedingPage(self.userid, 1, 200)
        cur_list_size, seeding_info = self.parseSeedingList(data.get("data"))
        totalPages = StringUtils.str_int(data.get("totalPages"))
        total = data.get("total")

        self.seeding = total
        self.seeding_size = 0
        self.seeding_size += cur_list_size
        all_seeding_info.extend(seeding_info)

        if totalPages > 1:
            # 循环获取下一页
            for index in range(2, totalPages):
                data = self.getSeedingPage(self.userid, index, 200)
                if data:
                    cur_list_size, seeding_info = self.parseSeedingList(data.get("data"))
                    self.seeding_size += cur_list_size
                    all_seeding_info.extend(seeding_info)

        self.seeding_info = json.dumps(all_seeding_info)

    def getSeedingPage(self, user_id, page_num, page_size):
        url = f"{self.site_url}/api/member/getUserTorrentList"
        params = {
            "pageNumber": page_num,
            "pageSize": page_size,
            "userid": user_id,
            "type": "SEEDING"
        }

        res =RequestUtils(
            headers=self._ua,
            content_type="application/json",
            accept_type="application/json",
            cookies=self._site_cookie,
            session=self._session,
            timeout=15
        ).post_res(url, json=params)

        if res and res.status_code == 200:
            result = res.json()
            if result and result.get("data"):
                return result.get("data")

        return None

    def parse(self):
        self._parse_favicon(self._index_html)
        user_info = self.get_user_profile()
        if user_info:
            self.username = user_info.get("username")

            memerberCount = user_info.get("memberCount")
            self.upload = StringUtils.num_filesize(memerberCount.get("uploaded"))
            self.download = StringUtils.num_filesize(memerberCount.get("downloaded"))
            self.ratio = memerberCount.get("shareRate")
            self.bonus = memerberCount.get("bonus")
            self.userid = user_info.get("id")
            self.user_level = user_info.get("role")
            self.join_at = user_info.get("createdDate")

            self.parse_seeding()

