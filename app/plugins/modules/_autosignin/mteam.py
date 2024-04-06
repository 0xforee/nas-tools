import time

from app.helper import ChromeHelper
from app.helper.cloudflare_helper import under_challenge
from app.plugins.modules._autosignin._base import _ISiteSigninHandler
from app.utils import MteamUtils
from config import Config


class MTeam(_ISiteSigninHandler):
    """
    学校签到
    """
    # 匹配的站点Url，每一个实现类都需要设置为自己的站点Url
    site_url = "m-team"

    @classmethod
    def match(cls, url):
        """
        根据站点Url判断是否匹配当前站点签到类，大部分情况使用默认实现即可
        :param url: 站点Url
        :return: 是否匹配，如匹配则会调用该类的signin方法
        """
        return url and url.find(cls.site_url) != -1

    def signin(self, site_info: dict):
        """
        执行签到操作
        :param site_info: 站点信息，含有站点Url、站点Cookie、UA等信息
        :return: 签到结果信息
        """
        site = site_info.get("name")
        site_cookie = site_info.get("cookie")
        ua = site_info.get("ua")
        sign_url = site_info.get("signurl")
        api_key = site_info.get("api_key")
        proxy = Config().get_proxies() if site_info.get("proxy") else None

        render = site_info.get("render")
        if render:
            # 首页
            chrome = ChromeHelper()
            if chrome.get_status():
                self.info(f"{site} 开始仿真签到")
                msg, html_text = self.__chrome_visit(chrome=chrome,
                                                     url=sign_url,
                                                     ua=ua,
                                                     site_cookie=site_cookie,
                                                     proxy=proxy,
                                                     site=site)

                # 仿真访问失败
                if msg:
                    return False, msg

                # 已签到
                self.info(f"签到成功")
                return True, f'【{site}】签到成功'
            else:
                self.error(f"chrome 状态异常")
                return False, f'仿真浏览器异常'
        else:
            #TODO 官方禁止调用
            api = "%s/api/member/updateLastBrowse"
            from urllib.parse import urlparse
            parse_result = urlparse(sign_url)
            api = api % (str(parse_result.scheme) + "://" + str(parse_result.hostname))
            res = MteamUtils.buildRequestUtils(
                headers=ua,
                api_key=api_key,
                proxies=Config().get_proxies() if site_info.get("proxy") else None,
                timeout=15
            ).post_res(url=api)

            if res and res.status_code == 200:
                self.info(f"{site} APIKEY 签到成功")
                return True, f'【{site}】APIKEY 签到成功'
            else:
                self.error(f"{site} APIKEY 签到失败{res} ")
                return False, f'{site} APIKEY 签到失败'

    def __chrome_visit(self, chrome, url, ua, site_cookie, proxy, site):
        if not chrome.visit(url=url, ua=ua, cookie=site_cookie, proxy=proxy):
            self.warn("%s 无法打开网站" % site)
            return f"【{site}】仿真签到失败，无法打开网站！", None
        # 检测是否过cf
        time.sleep(5)
        if under_challenge(chrome.get_html()):
            # 循环检测是否过cf
            cloudflare = chrome.pass_cloudflare()
            if not cloudflare:
                self.warn("%s 跳转站点失败" % site)
                return f"【{site}】仿真签到失败，跳转站点失败！", None
        # 获取html
        html_text = chrome.get_html()
        if not html_text:
            self.warn("%s 获取站点源码失败" % site)
            return f"【{site}】仿真签到失败，获取站点源码失败！", None
        if "魔力值" not in html_text:
            self.error(f"签到失败，站点无法访问")
            return f'【{site}】仿真签到失败，站点无法访问', None

        # 站点访问正常，返回html
        return None, html_text
