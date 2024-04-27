import json
import time

from app.conf import SystemConfig
from app.helper.cloudflare_helper import under_challenge
from app.plugins.modules._autosignin._base import _ISiteSigninHandler
from app.helper.sign_helper import SignChromeHelper
from app.sites import SiteConf
from app.utils import ExceptionUtils
from app.utils.types import SystemConfigKey
from config import Config
from lxml import etree
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as es
from selenium.webdriver.support.wait import WebDriverWait

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

    def __chrome_visit(self, chrome, url, ua, proxy, site):
        if not chrome.visit(url=url, ua=ua, proxy=proxy):
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
        #     return None, None
        #     self.warn("%s 获取站点源码失败" % site)
            return f"【{site}】仿真签到失败，获取站点源码失败！", None
        # if "魔力值" not in html_text:
        #     self.error(f"签到失败，站点无法访问")
        #     return f'【{site}】仿真签到失败，站点无法访问', None

        # 站点访问正常，返回html
        return None, html_text

    def signin(self, site_info: dict):
        """
        执行签到操作
        :param site_info: 站点信息，含有站点Url、站点Cookie、UA等信息
        :return: 签到结果信息
        """
        site = site_info.get("name")
        ua = site_info.get("ua")
        sign_url = site_info.get("signurl")
        proxy = Config().get_proxies() if site_info.get("proxy") else None

        chrome = SignChromeHelper()
        if chrome.get_status():
            self.info(f"{site} 开始仿真签到")
            # first, get html
            msg, html_text = self.__chrome_visit(chrome=chrome,
                                                 url=sign_url,
                                                 ua=ua,
                                                 proxy=proxy,
                                                 site=site)
            if not html_text:
                return False, f"【{site}】${msg}"

            # second, check if it is home
            if "魔力值" in html_text:
                return True, f"【{site}】签到成功"

            # third check if login page and try login
            value = SystemConfig().get(key=SystemConfigKey.CookieUserInfo)
            _, html_text, msg = self.try_login(chrome, html_text, value.get("username"), value.get("password"), value.get("two_step_code"))

            if not html_text:
                return False, f"【{site}】${msg}"

            # second, check if it is home
            if "魔力值" in html_text:
                return True, f"【{site}】签到成功"

            if "郵箱驗證碼" in html_text:
                return False, f"【{site}】触发邮箱登录，无法签到，请在站点管理处更新站点信息"

    def try_login(self, chrome,
                             html_text,
                             username,
                             password,
                             twostepcode=None,):
        """
        获取站点cookie和ua
        :param url: 站点地址
        :param username: 用户名
        :param password: 密码
        :param twostepcode: 两步验证
        :param ocrflag: 是否开启OCR识别
        :param proxy: 是否使用内置代理
        :return: cookie、ua、message
        """
        if not chrome or not username or not password:
            return None, None, "参数错误"

        # 站点配置
        login_conf = SiteConf().get_login_conf()
        # 查找用户名输入框
        html = etree.HTML(html_text)
        username_xpath = None
        for xpath in login_conf.get("username"):
            if html.xpath(xpath):
                username_xpath = xpath
                break
        if not username_xpath:
            return None, None, "未找到用户名输入框"
        # 查找密码输入框
        password_xpath = None
        for xpath in login_conf.get("password"):
            if html.xpath(xpath):
                password_xpath = xpath
                break
        if not password_xpath:
            return None, None, "未找到密码输入框"
        # 查找两步验证码
        twostepcode_xpath = None
        for xpath in login_conf.get("twostep"):
            if html.xpath(xpath):
                twostepcode_xpath = xpath
                break
        # 查找验证码输入框
        captcha_xpath = None
        for xpath in login_conf.get("captcha"):
            if html.xpath(xpath):
                captcha_xpath = xpath
                break
        # 查找验证码图片
        captcha_img_url = None
        if captcha_xpath:
            for xpath in login_conf.get("captcha_img"):
                if html.xpath(xpath):
                    captcha_img_url = html.xpath(xpath)[0]
                    break
            if not captcha_img_url:
                return None, None, "未找到验证码图片"
        # 查找登录按钮
        submit_xpath = None
        for xpath in login_conf.get("submit"):
            if html.xpath(xpath):
                submit_xpath = xpath
                break
        if not submit_xpath:
            return None, None, "未找到登录按钮"
        # 点击登录按钮
        try:
            submit_obj = WebDriverWait(driver=chrome.browser,
                                       timeout=6).until(es.element_to_be_clickable((By.XPATH,
                                                                                    submit_xpath)))
            if submit_obj:
                # 输入用户名
                chrome.browser.find_element(By.XPATH, username_xpath).send_keys(username)
                # 输入密码
                chrome.browser.find_element(By.XPATH, password_xpath).send_keys(password)
                # 提交登录
                submit_obj.click()
                # 等待页面刷新完毕
                WebDriverWait(driver=chrome.browser, timeout=5).until(es.staleness_of(submit_obj))
            else:
                return None, None, "未找到登录按钮"
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return None, None, "仿真登录失败：%s" % str(e)
        # 登录后的源码
        html_text = chrome.get_html()
        if not html_text:
            return None, None, "获取源码失败"

        return None, html_text, "获取页面成功"

