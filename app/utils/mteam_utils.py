from urllib.parse import urlparse

from app.utils import RequestUtils, StringUtils
from config import Config


class MteamUtils:

    @staticmethod
    def get_api_url(url):
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        index = parsed_url.hostname.index('m-team')
        last_domain = parsed_url.hostname[index:]
        return str(parsed_url.scheme) + "://" + 'api.' + last_domain

    @staticmethod
    def get_mteam_torrent_info(torrent_url, ua=None, proxy=False):
        api = "%s/api/torrent/detail"
        api = api % MteamUtils.get_api_url(torrent_url)
        torrent_id = torrent_url.split('/')[-1]
        req = MteamUtils.buildRequestUtils(api_key=MteamUtils.get_api_key(torrent_url), headers=ua, proxies=proxy).post_res(url=api, params={"id": torrent_id})

        if req and req.status_code == 200:
            return req.json().get("data")

        return None

    @staticmethod
    def test_connection(site_info):
        api = "%s/api/member/profile"
        site_url = site_info.get("signurl")
        api = api % MteamUtils.get_api_url(site_url)
        site_api_key = site_info.get("api_key")
        ua = site_info.get("ua")
        res = MteamUtils.buildRequestUtils(
            headers=ua,
            api_key=site_api_key,
            proxies=Config().get_proxies() if site_info.get("proxy") else None,
            timeout=15
        ).post_res(url=api)
        if res:
            if res.status_code == 200:
                user_info = res.json()
                if user_info and user_info.get("data"):
                    return True, "连接成功"
            else:
                return False, "连接失败：" + str(res.status_code)
        return False, "连接失败"

    @staticmethod
    def get_mteam_torrent_url(url, ua=None, referer=None, proxy=False):
        if url.find('api/rss/dl') != -1:
            return url
        api = "%s/api/torrent/genDlToken"
        api = api % MteamUtils.get_api_url(url)
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        torrent_id = parsed_url.path.split('/')[-1]

        req = MteamUtils.buildRequestUtils(
            headers=ua,
            api_key=MteamUtils.get_api_key(url),
            referer=referer,
            proxies=Config().get_proxies() if proxy else None
        ).post_res(url=api, params={"id": torrent_id})

        if req and req.status_code == 200:
            return req.json().get("data")

        return None

    @staticmethod
    def get_mteam_torrent_req(url, ua=None, referer=None, proxy=False):
        req = MteamUtils.buildRequestUtils(
            api_key=MteamUtils.get_api_key(url),
            headers=ua,
            referer=referer,
            proxies=Config().get_proxies() if proxy else None
        ).get_res(url=url, allow_redirects=True)

        return req

    @staticmethod
    def get_api_key(url):
        from app.sites import Sites
        sites = Sites()
        site_info = sites.get_sites(siteurl=url)
        if site_info:
            api_key = site_info.get("api_key")

            if api_key:
                return api_key

        return None

    @staticmethod
    def buildRequestUtils(cookies=None, api_key=None, headers=None, proxies=False, content_type=None, accept_type=None, session=None, referer=None, timeout=30):
        if api_key:
            # use api key
            return RequestUtils(headers=headers, api_key=api_key, timeout=timeout, referer=referer,
                                content_type=content_type, session=session, accept_type=accept_type,
                                proxies=Config().get_proxies() if proxies else None)
        return RequestUtils(headers=headers, cookies=cookies, timeout=timeout, referer=referer,
                            content_type=content_type, session=session, accept_type=accept_type,
                            proxies=Config().get_proxies() if proxies else None)

