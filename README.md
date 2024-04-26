# delOnedriveHistory
### 说明：
无论你是用SharePoint Online Management Shell还是DMS-shuttle的方式，你会发现无法完全清除Onedrive内的所有历史版本，本项目就是围绕此痛点所产生的问题来解决。

### 环境准备：
- chromium带user data;
- chrome以及对应版本的chromedriver;

### 推荐的操作步骤：
_powershell登录到Onedrive（全局管理员），开启禁用文件历史版本的选项，之后在web端设为此选项。之后使用本工具进行处理（仅保留最新的一版）.文件多可能需要一段时间来运行_
1. 开启禁用文件历史版本的选项

  `$UserCredential = Get-Credential`

  `Connect-SPOService -Url https://xxxxx-admin.sharepoint.com -Credential $UserCredential`

  `Set-SPOTenant -EnableMinimumVersionRequirement $False`

2. web端设置

![Snipaste1.png](Snipaste%2FSnipaste1.png)

![Snipaste2.png](Snipaste%2FSnipaste2.png)

3. 工具处理：收集&清除历史版本

<small>你可以直接使用Python环境来运行脚本，或者使用打包的exe程序</small>
- 首先在chroium手动登录一次
- 执行collectHistoryUrls 采集url
- 执行delHistory/&byeach删除（复制更多userdata以使用更多线程）


4. 最后去Onedrive删除回收站和第二回收站




### 其他
<small>没有其他</small>

