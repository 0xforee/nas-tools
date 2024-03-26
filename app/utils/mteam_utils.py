from urllib.parse import urlparse

from app.utils import RequestUtils
from config import Config


class MteamUtils:
    @staticmethod
    def get_mteam_torrent_info(torrent_url, cookie, ua=None, proxy=False):
        api = "%s/api/torrent/detail"
        from urllib.parse import urlparse
        parse_result = urlparse(torrent_url)
        api = api % (str(parse_result.scheme) + "://" + str(parse_result.hostname))
        torrent_id = torrent_url.split('/')[-1]
        req = MteamUtils.buildRequestUtils(cookie, ua, proxy).post_res(url=api, params={"id": torrent_id})

        if req and req.status_code == 200:
            return req.json().get("data")

        return None

    @staticmethod
    def mteam_sign(site_info):
        site_url = site_info.get("signurl")
        site_cookie = site_info.get("cookie")
        ua = site_info.get("ua")
        url = f"{site_url}api/member/profile"
        res = MteamUtils.buildRequestUtils(
            headers=ua,
            cookies=site_cookie,
            proxies=Config().get_proxies() if site_info.get("proxy") else None,
            timeout=15
        ).post_res(url=url)
        if res and res.status_code == 200:
            user_info = res.json()
            if user_info and user_info.get("data"):
                return True, "连接成功"
        return False, "Cookie已失效"

    @staticmethod
    def get_mteam_url(url, cookie=None, ua=None, referer=None, proxy=False):
        api = "%s/api/torrent/genDlToken"
        parse_result = urlparse(url)
        api = api % (str(parse_result.scheme) + "://" + str(parse_result.hostname))
        torrent_id = url.split('/')[-1]
        req = MteamUtils.buildRequestUtils(
            headers=ua,
            cookies=cookie,
            referer=referer,
            proxies=Config().get_proxies() if proxy else None
        ).post_res(url=api, params={"id": torrent_id})

        if req and req.status_code == 200:
            return req.json().get("data")

        return None

    @staticmethod
    def buildRequestUtils(cookies, headers=None, proxies=False, content_type=None, accept_type=None, session=None, referer=None, timeout=30):
        if cookies.find("=") != -1:
            return RequestUtils(headers=headers, cookies=cookies, timeout=timeout, referer=referer,
                                content_type=content_type, session=session, accept_type=accept_type,
                                proxies=Config().get_proxies() if proxies else None)
        else:
            # use api key
            return RequestUtils(headers=headers, api_key=cookies, timeout=timeout, referer=referer,
                                content_type=content_type, session=session, accept_type=accept_type,
                                proxies=Config().get_proxies() if proxies else None)
