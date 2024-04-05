from python_hosts import Hosts, HostsEntry

from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils import SystemUtils, IpUtils
from app.utils.types import EventType


class CustomHosts(_IPluginModule):
    # 插件名称
    module_name = "自定义Hosts"
    # 插件描述
    module_desc = "修改系统hosts文件，加速网络访问。"
    # 插件图标
    module_icon = "hosts.png"
    # 主题色
    module_color = "#02C4E0"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "thsrite"
    # 作者主页
    author_url = "https://github.com/thsrite"
    # 插件配置项ID前缀
    module_config_prefix = "customhosts_"
    # 加载顺序
    module_order = 11
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _hosts = []
    _enable = False

    @staticmethod
    def get_fields():
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': 'hosts',
                            'required': False,
                            'tooltip': 'hosts配置，会追加到系统hosts文件中生效',
                            'type': 'textarea',
                            'content':
                                {
                                    'id': 'hosts',
                                    'placeholder': '每行一个配置，格式为：ip host1 host2 ...',
                                    'rows': 10,
                                }
                        }
                    ],
                    [
                        {
                            'title': '错误hosts',
                            'required': False,
                            'tooltip': '错误的hosts配置会展示在此处，请修改上方hosts重新提交（错误的hosts不会写入系统hosts文件）',
                            'type': 'textarea',
                            'readonly': True,
                            'content':
                                {
                                    'id': 'err_hosts',
                                    'placeholder': '',
                                    'rows': 2,
                                }
                        }
                    ],
                    [
                        {
                            'title': '开启hosts同步',
                            'required': "",
                            'tooltip': '将自定义hosts更新到系统中生效，如因权限问题等无法更新到系统时此开关将自动关闭，此时需查看日志',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ]
                ]
            }
        ]

    def init_config(self, config=None):
        # 读取配置
        if config:
            self._enable = config.get("enable")
            self._hosts = config.get("hosts")
            if isinstance(self._hosts, str):
                self._hosts = str(self._hosts).split('\n')
            if self._enable and self._hosts:
                # 排除空的host
                new_hosts = []
                for host in self._hosts:
                    if host and host != '\n':
                        new_hosts.append(host.replace("\n", "") + "\n")
                self._hosts = new_hosts

                # 添加到系统
                error_flag, error_hosts = self.__add_hosts_to_system(self._hosts)
                self._enable = self._enable and not error_flag

                # 更新错误Hosts
                self.update_config({
                    "hosts": self._hosts,
                    "err_hosts": error_hosts,
                    "enable": self._enable
                })

    @EventHandler.register(EventType.PluginReload)
    def reload(self, event):
        """
        响应插件重载事件
        """
        plugin_id = event.event_data.get("plugin_id")
        if not plugin_id:
            return
        if plugin_id != self.__class__.__name__:
            return
        return self.init_config(self.get_config())

    @staticmethod
    def __read_system_hosts():
        """
        读取系统hosts对象
        """
        # 获取本机hosts路径
        if SystemUtils.is_windows():
            hosts_path = r"c:\windows\system32\drivers\etc\hosts"
        else:
            hosts_path = '/etc/hosts'
        # 读取系统hosts
        return Hosts(path=hosts_path)

    def __add_hosts_to_system(self, hosts):
        """
        添加hosts到系统
        """
        # 系统hosts对象
        system_hosts = self.__read_system_hosts()
        # 过滤掉插件添加的hosts
        orgin_entries = []
        for entry in system_hosts.entries:
            if entry.entry_type == "comment" and entry.comment == "# CustomHostsPlugin":
                break
            orgin_entries.append(entry)
        system_hosts.entries = orgin_entries
        # 新的有效hosts
        new_entrys = []
        # 新的错误的hosts
        err_hosts = []
        err_flag = False
        for host in hosts:
            if not host:
                continue
            host_arr = str(host).split()
            try:
                host_entry = HostsEntry(entry_type='ipv4' if IpUtils.is_ipv4(str(host_arr[0])) else 'ipv6',
                                        address=host_arr[0],
                                        names=host_arr[1:])
                new_entrys.append(host_entry)
            except Exception as err:
                err_hosts.append(host + "\n")
                self.error(f"{host} 格式转换错误：{str(err)}")

        # 写入系统hosts
        if new_entrys:
            try:
                # 添加分隔标识
                system_hosts.add([HostsEntry(entry_type='comment', comment="# CustomHostsPlugin")])
                # 添加新的Hosts
                system_hosts.add(new_entrys)
                system_hosts.write()
                self.info("更新系统hosts文件成功")
            except Exception as err:
                err_flag = True
                self.error(f"更新系统hosts文件失败：{str(err) or '请检查权限'}")
        return err_flag, err_hosts

    def get_state(self):
        return self._enable and self._hosts and self._hosts[0]

    def stop_service(self):
        """
        退出插件
        """
        pass
