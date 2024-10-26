import os
from xml.etree.ElementTree import ElementTree, Element

from jinja2 import Template
from flask import Flask, request
from app.helper import ThreadHelper
from app.plugins.modules._base import _IPluginModule
from threading import Event, Thread
from app.sites.sites import Sites
from http.server import HTTPServer, SimpleHTTPRequestHandler

from app.utils import RequestUtils, MteamUtils
from config import Config
import html


_plugin = None

class Request(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

    def do_GET(self):
        if self.requestline.find('rss_pub.xml') != -1:
            global _plugin
            content = _plugin.fetch_new_item()

            self.send_response(200)
            self.send_header("Content-Type", "application/xml;charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
            return

        super().do_GET()
        print('get finished')


class RssTorrent:
    def __init__(self):
        self.id = ""
        self.title = ""
        self.enclosure = ""
        self.link = ""
        self.size = ""
        self.pubdate = ""
        self.category = ""
        # 标记是否刷流（free + 限时 7 日）
        self.mark_brush = False


class MteamRssGen(_IPluginModule):
    # 插件名称
    module_name = "馒头大包监控"
    # 插件描述
    module_desc = "后台服务定期监控馒头大包，并发布 RSS"
    # 插件图标
    module_icon = "mteam_rss.png"
    # 主题色
    module_color = "#4179F4"
    # 插件版本
    module_version = "1.1"
    # 插件作者
    module_author = "0xforee"
    # 作者主页
    author_url = "https://github.com/0xforee"
    # 插件配置项ID前缀
    module_config_prefix = "mteam_rss_gen"
    # 加载顺序
    module_order = 0
    # 可使用的用户级别
    auth_level = 2

    # 上次运行结果属性
    _last_run_results_list = []

    # 私有属性
    _server = None

    # 设置开关
    _enable = False
    # 任务执行间隔
    _site_base_url = None
    _site_key = "m-team"
    _site_ua = ""
    _site_api_key = ""
    _site_conf = None
    _search_api = "%s/api/torrent/search"
    _torrent_min_size = None
    _watch_categories = None
    _last_rss_torrents = None

    # 退出事件
    _event = Event()

    def init_config(self, config: dict = None):
        global _plugin
        _plugin = self
        for site in Sites().get_sites():
            sign_url = site.get('signurl')
            if sign_url and sign_url.find(self._site_key) != -1:
                self._site_conf = site
                from urllib.parse import urlparse
                parse_result = urlparse(sign_url)
                self._site_base_url = str(parse_result.scheme) + "://" + str(parse_result.hostname) + '/'

        if config:
            self._enable = config.get("enabled")
            self._torrent_min_size = config.get("torrent_min_size") or 0
            self._watch_categories = config.get("watch_categories") or ['adult']

        # 停止现有任务
        self.stop_service()
        #
        # 启动服务
        if self.get_state():
            self.start_http_server()

    def start_http_server(self):
        # rss_server =
        try:
            self._server = HTTPServer(('0.0.0.0', 8001), Request)
            http_thread = Thread(target=self._server.serve_forever)
            http_thread.start()
        except Exception as e:
            self.error("found some error: " + str(e))
        self.info('Starting mteam rss server, listen at % localhost:' + str(self._server.server_port))

    def get_state(self):
        return self._enable

    def stop_service(self):
        """
        停止服务
        """
        try:
            self.info("stop mt rss server")
            if self._server:
                self._server.shutdown()
                self._server = None
        except Exception as e:
            print(str(e))

    def get_rss_page(self):
        self.info("start generate rss page")

        """
        RSS 的标准模板
        :return: 标题，页面内容，确定按钮响应函数
        """



    @staticmethod
    def get_fields():
        return [
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '开启',
                            'required': "",
                            'tooltip': '开启后会启动 RSS 生成服务，将 http://127.0.0.1:8001/rss_pub.xml 填入馒头刷流任务 RSS 地址使用',
                            'type': 'switch',
                            'id': 'enabled',
                        },
                    ]
                ]
            },
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '种子体积最小值（GB）',
                            'required': "required",
                            'tooltip': '大于配置值的种子才会被监控到，默认为 0',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'torrent_min_size',
                                    'placeholder': '0',
                                }
                            ]
                        },
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '监控类别',
                'required': "required",
                'tooltip': '监控选中的类别，必选！！',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'watch_categories',
                            'type': 'form-selectgroup',
                            'content': {
                                'adult': {
                                    'id': 'adult',
                                    'radio': True,
                                    'name': '成人',
                                },
                                'normal': {
                                    'id': 'normal',
                                    'name': '综合',
                                },
                                'movie': {
                                    'id': 'movie',
                                    'name': '电影',
                                },
                                'tvshow': {
                                    'id': 'tvshow',
                                    'name': '剧集',
                                }
                            }
                        },
                    ]
                ]
            },
        ]

    def fetch_new_item(self):
        self.info('fetch new torrents start')
        search_url = self._search_api % MteamUtils.get_api_url(self._site_base_url)
        # 所有需要刷流的种子
        torrents_info_array = []

        for mode in self._watch_categories:
            param_json = {
                "pageNumber": 1,
                "pageSize": 100,
                "keyword": "",
                "visible": 1,
                "mode": mode
            }

            proxy = Config().get_proxies() if self._site_conf.get("proxy") else None
            api_key = self._site_conf.get("api_key")
            ua = self._site_conf.get("ua")
            rss_request = RequestUtils(api_key=api_key,
                                   headers=ua,
                                   content_type="application/json",
                                   proxies=proxy
                                   )
            res = rss_request.post_res(url=search_url, json=param_json)
            file_id = search_url + mode
            if res:
                if res.status_code == 200:
                    # fetch success, parse
                    res_torrents = self.parse_response(res.json())
                    self.info(f"MT RSS Generator:{mode}, found {len(res_torrents)} torrents")
                    # res_torrents = parse_html(res.text)
                    torrents_info_array.extend(res_torrents)
                else:
                    self.info(f"MT RSS Generator:{mode}," + str(res.status_code) + f', get rss from mteam {file_id}' + str(res))
            else:
                self.info(f"MT RSS Generator:{mode}, response: " + str(res) + " is None")

        # 过滤非刷流的种子
        brush_torrents = []
        for torrent_info in torrents_info_array:
            if torrent_info.mark_brush:
                brush_torrents.append(torrent_info)

        template = """<?xml version="1.0" encoding="UTF-8"?>
                <rss version="2.0">
                    <channel>
                        <title>
                            <![CDATA[ M-Team - TP Torrents ]]>
                        </title>
                        <link>https://kp.m-team.cc</link>
                        <description>
                            <![CDATA[ Latest torrents from M-Team - TP - Working ]]>
                        </description>
                        <image>
                            <title>
                                <![CDATA[ M-Team - TP Torrents ]]>
                            </title>
                            <link>https://kp.m-team.cc</link>
                            <url>https://kp.m-team.cc/pic/rss_logo.jpg</url>
                        </image>
                        <language>zh-tw</language>
                        <copyright>Copyright (c) M-Team - TP 2012-2023, all rights reserved</copyright>
                        <managingEditor>webmaster@m-team.cc (M-Team - TP Admin)</managingEditor>
                        <webMaster>webmaster@m-team.cc (M-Team - TP Webmaster)</webMaster>
                        <generator>NexusPHP RSS Generator</generator>
                        <ttl>60</ttl>
                        <lastBuildDate>Tue, 18 Apr 2023 20:38:06 +0800</lastBuildDate>
                        {% for rssTorrent in Torrents %}
                            <item>
                                <title>{{ rssTorrent.title }}</title>
                                <description/>
                                <link>{{ rssTorrent.link }}</link>
                                <author>anonymous@kp.m-team.cc (anonymous)</author>
                                <pubDate>{{ rssTorrent.pubdate }}</pubDate>
                                <guid isPermaLink="false">{{ rssTorrent.enclosure }}</guid>
                                <enclosure length="{{ rssTorrent.size }}" type="application/x-bittorrent"
                                           url="{{ rssTorrent.enclosure }}"/>
                                <category>{{ rssTorrent.category }}</category>
                            </item>
                        {% endfor %}
                    </channel>
                </rss>
                        """
        return Template(template).render(Torrents=brush_torrents)

    def parse_response(self, res):
        data = res.get('data')
        tr_list = data.get('data')
        torrents = []
        for tr in tr_list:
            page_url = self._site_base_url + 'detail/' + tr.get('id')
            status = tr.get('status')
            torrent_info = RssTorrent()
            torrent_info.id = tr.get('id')
            torrent_info.title = html.escape(tr.get('name'))
            # pubdate
            pubdate = tr.get('createdDate')
            import time
            str_time = (time.strptime(pubdate, "%Y-%m-%d %H:%M:%S"))
            torrent_info.pubdate = time.strftime("%a, %d %b %Y %H:%M:%S +0800", str_time)

            torrent_info.size = tr.get('size')
            torrent_info.enclosure = page_url
            torrent_info.link = page_url
            torrent_info.category = tr.get('category')
            torrent_info.mark_brush = False
            if self.match_size(torrent_info.size):
                if self.is_free_or_promote(tr):
                    torrent_info.mark_brush = True

            torrents.append(torrent_info)
        if not torrents:
            self.info("found 0 torrents match")

        return torrents

    def is_free_or_promote(self, tr):
        try:
            status = tr.get('status')
            discount = status.get('discount')
            if discount.find('FREE') != -1:
                return True
            else:
                mallSingleFree = status.get('mallSingleFree')
                if mallSingleFree and mallSingleFree.get('endDate'):
                    endDay = mallSingleFree.get('endDate')
                    from datetime import datetime

                    # Define the given date as a string and the current date
                    given_date = datetime.strptime(endDay, '%Y-%m-%d %H:%M:%S')
                    current_date = datetime.now()

                    # Check if the given date is past the current date
                    is_expired = current_date > given_date
                    if not is_expired:
                        return True
        except Exception as e:
            self.error(e)
        return False

    def match_size(self, torrent_size):
        limit = int(self._torrent_min_size) * 1024 ** 3
        torrent_size = int(torrent_size)
        if torrent_size > limit:
            return True

        return False
