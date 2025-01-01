import random
import time
from functools import lru_cache

from lxml import etree
import log
from app.helper import ChromeHelper
from app.utils import ExceptionUtils, StringUtils, RequestUtils, MteamUtils
from app.utils.commons import singleton
from config import Config
from web.backend.pro_user import ProUser


@singleton
class SiteConf:
    user = None
    # 站点签到支持的识别XPATH
    _SITE_CHECKIN_XPATH = [
        '//a[@id="signed"]',
        '//a[contains(@href, "attendance")]',
        '//a[contains(text(), "签到")]',
        '//a/b[contains(text(), "签 到")]',
        '//span[@id="sign_in"]/a',
        '//a[contains(@href, "addbonus")]',
        '//input[@class="dt_button"][contains(@value, "打卡")]',
        '//a[contains(@href, "sign_in")]',
        '//a[contains(@onclick, "do_signin")]',
        '//a[@id="do-attendance"]',
        '//shark-icon-button[@href="attendance.php"]'
    ]

    # 站点详情页字幕下载链接识别XPATH
    _SITE_SUBTITLE_XPATH = [
        '//td[@class="rowhead"][text()="字幕"]/following-sibling::td//a/@href',
    ]

    # 站点登录界面元素XPATH
    _SITE_LOGIN_XPATH = {
        "username": [
            '//input[@name="username"]',
            '//input[@id="form_item_username"]',
            '//input[@id="username"]'
        ],
        "password": [
            '//input[@name="password"]',
            '//input[@id="form_item_password"]',
            '//input[@id="password"]'
        ],
        "captcha": [
            '//input[@name="imagestring"]',
            '//input[@name="captcha"]',
            '//input[@id="form_item_captcha"]'
        ],
        "captcha_img": [
            '//img[@alt="CAPTCHA"]/@src',
            '//img[@alt="SECURITY CODE"]/@src',
            '//img[@id="LAY-user-get-vercode"]/@src',
            '//img[contains(@src,"/api/getCaptcha")]/@src'
        ],
        "submit": [
            '//input[@type="submit"]',
            '//button[@type="submit"]',
            '//button[@lay-filter="login"]',
            '//button[@lay-filter="formLogin"]',
            '//input[@type="button"][@value="登录"]'
        ],
        "error": [
            "//table[@class='main']//td[@class='text']/text()"
        ],
        "twostep": [
            '//input[@name="two_step_code"]',
            '//input[@name="2fa_secret"]'
        ]
    }

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.user = ProUser()

    def get_checkin_conf(self):
        return self._SITE_CHECKIN_XPATH

    def get_subtitle_conf(self):
        return self._SITE_SUBTITLE_XPATH

    def get_login_conf(self):
        return self._SITE_LOGIN_XPATH

    def get_grap_conf(self, url=None):
        if not url:
            return self.user.get_brush_conf()
        for k, v in self.user.get_brush_conf().items():
            if StringUtils.url_equal(k, url):
                return v
        return {}

    def check_torrent_attr(self, torrent_url, cookie, ua=None, proxy=False):
        """
        检验种子是否免费，当前做种人数
        :param torrent_url: 种子的详情页面
        :param cookie: 站点的Cookie
        :param ua: 站点的ua
        :param proxy: 是否使用代理
        :return: 种子属性，包含FREE 2XFREE HR PEER_COUNT等属性
        """
        ret_attr = {
            "free": False,
            "2xfree": False,
            "hr": False,
            "peer_count": 0,
            "free_deadline": ""
        }
        if not torrent_url:
            return ret_attr

        if torrent_url.find('m-team') != -1:
            info = MteamUtils.get_mteam_torrent_info(torrent_url, ua, proxy)
            if info:
                status = info.get('status')
                discount = status.get('discount')
                if discount == 'FREE':
                    ret_attr["free"] = True
                elif discount == '_2X_FREE':
                    ret_attr["free"] = True
                    ret_attr["2xfree"] = True
                ret_attr["free_deadline"] = status.get('toppingEndTime')
                ret_attr["peer_count"] = int(status.get("seeders"))

                # 限免种子包含在 mallSingleFree 中
                mallSingleFree = status.get('mallSingleFree')
                if mallSingleFree and mallSingleFree.get('endDate'):
                    endDay = mallSingleFree.get('endDate')
                    ret_attr["free"] = True
                    ret_attr["free_deadline"] = endDay
            return ret_attr

        xpath_strs = self.get_grap_conf(torrent_url)
        if not xpath_strs:
            return ret_attr
        html_text = self.__get_site_page_html(url=torrent_url,
                                              cookie=cookie,
                                              ua=ua,
                                              render=xpath_strs.get('RENDER'),
                                              proxy=proxy)
        if not html_text:
            return ret_attr
        try:
            html = etree.HTML(html_text)
            # 检测2XFREE
            for xpath_str in xpath_strs.get("2XFREE"):
                if html.xpath(xpath_str):
                    ret_attr["free"] = True
                    ret_attr["2xfree"] = True
            # 检测FREE
            for xpath_str in xpath_strs.get("FREE"):
                if html.xpath(xpath_str):
                    ret_attr["free"] = True
            # 检测限时信息，result为空表示未找到 限时信息
            try:
                free_ddl = ""
                title_xpath_str = "//h1[@id='top']//span"
                result = html.xpath(title_xpath_str)
                if len(result) > 0:
                    free_ddl = self.__parse_free_deadline(result[0].text)
                else:
                    free_ddl_pattern = xpath_strs.get("FREE_DDL")
                    if free_ddl_pattern:
                        for xpath_str in free_ddl_pattern:
                            result = html.xpath(xpath_str)
                            if len(result) > 0:
                                # get title attr first
                                ddl_str_2 = result[0].get('title')
                                if ddl_str_2:
                                    free_ddl = self.__parse_free_ddl_2(ddl_str_2)
                                else:
                                    free_ddl = self.__parse_free_deadline(result[0].text)

                ret_attr["free_deadline"] = free_ddl
            except Exception as err:
                ExceptionUtils.exception_traceback(err)
            # 检测HR
            for xpath_str in xpath_strs.get("HR"):
                if html.xpath(xpath_str):
                    ret_attr["hr"] = True
            # 检测PEER_COUNT当前做种人数
            for xpath_str in xpath_strs.get("PEER_COUNT"):
                peer_count_dom = html.xpath(xpath_str)
                if peer_count_dom:
                    peer_count_str = ''.join(peer_count_dom[0].itertext())
                    peer_count_digit_str = ""
                    for m in peer_count_str:
                        if m.isdigit():
                            peer_count_digit_str = peer_count_digit_str + m
                        if m == " ":
                            break
                    ret_attr["peer_count"] = int(peer_count_digit_str) if len(peer_count_digit_str) > 0 else 0
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
        # 随机休眼后再返回
        time.sleep(round(random.uniform(1, 5), 1))
        return ret_attr

    def __parse_free_ddl_2(self, ddl_str: str):
        """
        解析限免时间:
        "2025-01-02 00:00:17"
        转换时间格式：%Y%m%d_%H%M
        返回，转换后时间 20250102_0000
        """
        free_deadline_str = ""
        try:
            import datetime
            # Parse the time string into a datetime object
            dt = datetime.datetime.strptime(ddl_str, "%Y-%m-%d %H:%M:%S")

            # Format the datetime object into the desired format
            free_deadline_str = dt.strftime("%Y%m%d_%H%M")
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            # 如果没有限时信息，就直接crash掉了，返回空
            log.debug("Parse Deadline Error, origin: %s " % free_deadline_str)

        return free_deadline_str


    def __parse_free_deadline(self, deadline_str: str):
        """
        解析限免时间：
        MTEAM: 2日23時11分
        hdmayi:1天23时48分钟
        转换时间格式：%Y%m%d_%H%M
        返回：转换后时间 20230715_2310
        """
        free_deadline_str = ""
        if not deadline_str:
            return free_deadline_str
        try:
            import re
            free_deadline_re_day_pattern = r'(\d+)[天|日]'
            free_deadline_re_hour_pattern = r'(\d+)[時|时]'
            free_deadline_re_minutes_pattern = r'(\d+)[分]'
            day_result = re.search(free_deadline_re_day_pattern, deadline_str)
            hour_result = re.search(free_deadline_re_hour_pattern, deadline_str)
            minutes_result = re.search(free_deadline_re_minutes_pattern, deadline_str)
            day_str = (day_result.group(1) if day_result and len(day_result.groups()) > 0 else "")
            hour_str = (hour_result.group(1) if hour_result and len(hour_result.groups()) > 0 else "")
            min_str = (minutes_result.group(1) if minutes_result and len(minutes_result.groups()) > 0 else "")

            day = int(day_str if day_str else 0)
            hour = int(hour_str if hour_str else 0)
            min = int(min_str if min_str else 0)
            if day > 0 or hour > 0 or min > 0:
                import datetime
                res = datetime.datetime.now() + datetime.timedelta(days=day, hours=hour, minutes=min)
                free_deadline_str = res.strftime("%Y%m%d_%H%M")
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            # 如果没有限时信息，就直接crash掉了，返回空
            log.debug("Parse Deadline Error, origin: %s " % deadline_str)

        return free_deadline_str

    @staticmethod
    @lru_cache(maxsize=128)
    def __get_site_page_html(url, cookie, ua, render=False, proxy=False):
        chrome = ChromeHelper(headless=True)
        if render and chrome.get_status():
            # 开渲染
            if chrome.visit(url=url, cookie=cookie, ua=ua, proxy=proxy):
                # 等待页面加载完成
                time.sleep(10)
                return chrome.get_html()
        else:
            res = RequestUtils(
                cookies=cookie,
                headers=ua,
                proxies=Config().get_proxies() if proxy else None
            ).get_res(url=url)
            if res and res.status_code == 200:
                res.encoding = res.apparent_encoding
                return res.text
        return ""
