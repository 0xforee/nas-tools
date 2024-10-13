# -*- coding: utf-8 -*-
import json
import re
from abc import ABC

from lxml import etree

import log
from app.sites.siteuserinfo._base import _ISiteUserInfo, SITE_BASE_ORDER
from app.utils import StringUtils, MteamUtils
from app.utils.types import SiteSchema


class MteamSiteUserInfo(_ISiteUserInfo):

    _roleToLevelMap = {
        '1': 'User',
        '2': 'Power User',
        '3': 'Elite User',
        '4': 'Crazy User',
        '5': 'Insane User',
        '6': 'Veteran User',
        '7': 'Extreme User',
        '8': 'Ultimate User',
        '9': 'Nexus Master',
        '10': 'VIP',
        '17': 'Offer memberStaff',
        '18': 'bet memberStaff',
        '12': '巡查',
        '11': '職人',
        '13':'總版',
        '14': '總管',
        '15': '維護開發員',
        '16': '站長',

    }
    def _parse_message_unread_links(self, html_text, msg_links):
        pass

    def _parse_site_page(self, html_text):
        pass

    def _parse_user_base_info(self, html_text):
        pass

    def _parse_user_traffic_info(self, html_text):
        pass

    def _parse_user_torrent_seeding_info(self, html_text, multi_page=False):
        pass

    def _parse_user_detail_info(self, html_text):
        pass

    def _parse_message_content(self, html_text):
        pass

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
        api = "%s/api/member/profile"
        api = api % MteamUtils.get_api_url(self.site_url)
        res = MteamUtils.buildRequestUtils(
            headers=self._ua,
            api_key=MteamUtils.get_api_key(self.site_url),
            timeout=15
        ).post_res(url=api)
        if res:
            if res.status_code == 200:
                user_info = res.json()
                if user_info and user_info.get("data"):
                    return True, "获取用户信息成功"
            else:
                return False, f"获取用户信息失败：{res.status_code}"

        return False, "连接馒头失败"

    def get_user_profile(self):
        api = "%s/api/member/profile"
        api = api % MteamUtils.get_api_url(self.site_url)
        res = MteamUtils.buildRequestUtils(
            headers=self._ua,
            api_key=MteamUtils.get_api_key(self.site_url),
            session=self._session,
            timeout=15
        ).post_res(url=api)
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
        api = "%s/api/member/getUserTorrentList"
        api = api % MteamUtils.get_api_url(self.site_url)
        params = {
            "pageNumber": page_num,
            "pageSize": page_size,
            "userid": user_id,
            "type": "SEEDING"
        }

        res = MteamUtils.buildRequestUtils(
            headers=self._ua,
            content_type="application/json",
            accept_type="application/json",
            api_key=MteamUtils.get_api_key(self.site_url),
            session=self._session,
            timeout=15
        ).post_res(api, json=params)

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
            self.user_level = self._roleToLevelMap.get(user_info.get("role"))
            self.join_at = user_info.get("createdDate")

            memberStatus = user_info.get("memberStatus")
            self.last_seen = memberStatus.get('lastBrowse')

            self.parse_seeding()
        else:
            self.seeding_info = ''

