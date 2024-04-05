import log
from app.utils import StringUtils
from app.utils.types import DownloaderType
from config import Config
from app.downloader.client._base import _IDownloadClient
from app.downloader.client._pypan115 import PyPan115


class Pan115(_IDownloadClient):

    schema = "pan115"
    # 下载器ID
    client_id = "pan115"
    client_type = DownloaderType.PAN115
    client_name = DownloaderType.PAN115.value
    _client_config = {}

    _client = None
    cookie = None
    lasthash = None
    download_dir = []
    def __init__(self, config=None):
        if config:
            self._client_config = config
        self.init_config()
        self.connect()

    def init_config(self):
        if self._client_config:
            self.cookie = self._client_config.get("cookie")
            self.download_dir = self._client_config.get('download_dir') or []
            if self.cookie:
                self._client = PyPan115(cookie=self.cookie)

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.client_id, cls.client_type, cls.client_name] else False

    def connect(self):
        self._client.login()

    def get_status(self):
        if not self._client:
            return False
        ret = self._client.login()
        if not ret:
            log.info(self._client.err)
            return False
        return True

    def get_torrents(self, ids=None, status=None, **kwargs):
        tlist = []
        if not self._client:
            return tlist
        ret, tasks = self._client.gettasklist(page=1)
        if not ret:
            log.info(f"【{self.client_type}】获取任务列表错误：{self._client.err}")
            return tlist
        if tasks:
            for task in tasks:
                if ids:
                    if task.get("info_hash") not in ids:
                        continue
                if status:
                    if task.get("status") not in status:
                        continue
                ret, tdir = self._client.getiddir(task.get("file_id"))
                task["path"] = tdir
                tlist.append(task)

        return tlist or []

    def get_completed_torrents(self, **kwargs):
        return self.get_torrents(status=[2])

    def get_downloading_torrents(self, **kwargs):
        return self.get_torrents(status=[0, 1])

    def remove_torrents_tag(self, **kwargs):
        pass

    def get_transfer_task(self, **kwargs):
        pass

    def get_remove_torrents(self, **kwargs):
        return []

    def add_torrent(self, content, download_dir=None, **kwargs):
        if not self._client:
            return False
        if isinstance(content, str):
            ret, self.lasthash = self._client.addtask(tdir=download_dir, content=content)
            if not ret:
                log.error(f"【{self.client_type}】添加下载任务失败：{self._client.err}")
                return None
            return self.lasthash
        else:
            log.info(f"【{self.client_type}】暂时不支持非链接下载")
            return None

    def delete_torrents(self, delete_file, ids):
        if not self._client:
            return False
        return self._client.deltask(thash=ids)

    def start_torrents(self, ids):
        pass

    def stop_torrents(self, ids):
        pass

    def set_torrents_status(self, ids, **kwargs):
        return self.delete_torrents(ids=ids, delete_file=False)

    def get_download_dirs(self):
        return []

    def change_torrent(self, **kwargs):
        pass

    def get_downloading_progress(self, **kwargs):
        """
        获取正在下载的种子进度
        """
        Torrents = self.get_downloading_torrents()
        DispTorrents = []
        for torrent in Torrents:
            # 进度
            progress = round(torrent.get('percentDone'), 1)
            state = "Downloading"
            _dlspeed = StringUtils.str_filesize(torrent.get('peers'))
            _upspeed = StringUtils.str_filesize(torrent.get('rateDownload'))
            speed = "%s%sB/s %s%sB/s" % (chr(8595), _dlspeed, chr(8593), _upspeed)
            DispTorrents.append({
                'id': torrent.get('info_hash'),
                'name': torrent.get('name'),
                'speed': speed,
                'state': state,
                'progress': progress
            })
        return DispTorrents

    def set_speed_limit(self, **kwargs):
        """
        设置速度限制
        """
        pass

    def get_type(self):
        return self.client_type

    def get_files(self, tid):
        pass

    def recheck_torrents(self, ids):
        pass

    def set_torrents_tag(self, ids, tags):
        pass