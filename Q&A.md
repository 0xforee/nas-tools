## 常见问题

### 1. 启动inotify报错/无法自动目录同步

> 问题描述
> 无法启动，日志报inotify instance limit reached、inotify watch limit reached等与inotify相关错误
> 目录同步无法自动同步或只有部份目录正常，但在服务中手动启动可以正常同步

解决办法：
* 宿主机上（不是docker容器里），执行以下命令：
 ```bash
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
echo fs.inotify.max_user_instances=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```
* 插件-定时目录同步

### 2. 启动报错数据库no such column
> 问题描述
> 启动报错数据库no such column

解决办法：
* [Sqlite浏览器](https://github.com/sqlitebrowser/sqlitebrowser)打开config文件夹下user.db
* 删除alembic_version表后重启

### 3. Nginx-Proxy-Manager无法申请/更新Let's Encrypt证书
> 问题描述
> Nginx-Proxy-Manager无法申请/更新Let's Encrypt证书

解决办法：
* 无法通过DNSpod申请, 进入容器，执行命令
```bash
pip install certbot-dns-dnspod
```

* 无法更新/自动更新
```bash
进入容器，执行命令 pip install zope
```

* pip使用代理
```
pip install xxx --proxy=http://ip:port
```

### 4. 消息通知内容无法跳转
> 问题描述
> 消息通知内容无法跳转（包含“点击选择下载”的消息中，没有包含查看详情的入口）

解决办法：
* 设置-基础设置-系统-外网访问地址

### 5. 电影/电视剧订阅一直队列中
> 问题描述
> 电影/电视剧订阅添加后，一直在队列中
> 需手动刷新订阅开始搜索或订阅

解决办法：
* 订阅如启用有订阅站点, 请在设置-基础设置-服务-订阅RSS周期设置启用
* 订阅如启用有搜索站点, 请在设置-基础设置-服务-订阅搜索周期设置启用
* 添加后点击订阅，选择刷新

### 6. 目录同步文件重复转移
> 问题描述
> 设置-基础设置-媒体-重命名格式中包含{releaseGroup}
> 文件转移方式为目录同步
> 转移后，出现重复的转移文件（制作组等后缀不同）

解决办法：
* 目录同步设置时，目的目录不要在源目录下

### 7. 识别转移错误码-1
> 问题描述
> 识别转移错误码-1

解决办法：
* 硬链接跨盘，转移前后目录根目录需相同
* 群晖中，不同的共享文件夹会被系统认为是跨盘

### 8. 电视剧订阅在完结前自动删除
> 问题描述
> 电视剧订阅在完结前自动删除

解决办法：
*  TMDB词条未更新集数/下载资源无法识别集数
*  订阅中设置总集数