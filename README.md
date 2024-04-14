![logo-blue](https://user-images.githubusercontent.com/51039935/197520391-f35db354-6071-4c12-86ea-fc450f04bc85.png)
# NAS媒体库管理工具


[![GitHub stars](https://img.shields.io/github/stars/0xforee/nas-tools?style=plastic)](https://github.com/0xforee/nas-tools/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/0xforee/nas-tools?style=plastic)](https://github.com/0xforee/nas-tools/network/members)
[![GitHub issues](https://img.shields.io/github/issues/0xforee/nas-tools?style=plastic)](https://github.com/0xforee/nas-tools/issues)
[![GitHub license](https://img.shields.io/github/license/0xforee/nas-tools?style=plastic)](https://github.com/0xforee/nas-tools/blob/master/LICENSE.md)
[![Docker pulls](https://img.shields.io/docker/pulls/0xforee/nas-tools?style=plastic)](https://hub.docker.com/r/0xforee/nas-tools)
[![Platform](https://img.shields.io/badge/platform-amd64/arm64-pink?style=plastic)](https://hub.docker.com/r/0xforee/nas-tools)

Docker：https://hub.docker.com/repository/docker/0xforee/nas-tools  

TG 交流群：https://t.me/nastoolsolder  
TG 通知频道：https://t.me/ntolder_notify


## 功能： 

1. 优化用户认证
2. 优化新手刷流体验
1. 刷流任务优化：
   * 增加部分下载能力（拆包），最大效益提升刷流能力
   * 增加限免到期检测能力
   * 刷流界面增加详细信息展示
3. 支持 BT 能力和内置 BT 站点，可以索引和下载 BT 磁链和种子文件
4. 支持 jackett 和 prowlarr 索引器
5. 增加一些入口的快捷跳转能力
6. 完美支持 Mteam 新架构

详细参考 [这里](diff.md)。  

## 安装
### 1、Docker
```
docker pull 0xforee/nas-tools:latest
```
教程见 [这里](docker/readme.md) 。

如无法连接Github，注意不要开启自动更新开关(NASTOOL_AUTO_UPDATE=false)，将NASTOOL_CN_UPDATE设置为true可使用国内源加速安装依赖。

### 2、本地运行
python3.10版本，需要预安装cython，如发现缺少依赖包需额外安装：
```
git clone -b master https://github.com/0xforee/nas-tools --recurse-submodule 
python3 -m pip install -r requirements.txt
export NASTOOL_CONFIG="/xxx/config/config.yaml"
nohup python3 run.py & 
```


## 免责声明
1) 本软件不提供任何内容，仅作为辅助工具简化用户手工操作，对用户的行为及内容毫不知情，使用本软件产生的任何责任需由使用者本人承担。
2) 本软件代码开源，基于开源代码进行修改，人为去除相关限制导致软件被分发、传播并造成责任事件的，需由代码修改发布者承担全部责任。同时按AGPL-3.0开源协议要求，基于此软件代码的所有修改必须开源。
3) 所有搜索结果均来自源站，本软件不承担任何责任
3) 本软件仅供学习交流，请保持低调，勿公开传播
