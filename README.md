# delOnedriveHistory
说明：
无论你是用SharePoint Online Management Shell还是DMS-shuttle的方式，你会发现无法完全清除Onedrive内的所有历史版本，本项目就是围绕此痛点来解决的。
推荐的操作步骤：
1.首次powershell登录到Onedrive（全局管理员），开启禁用文件历史版本的选项，之后在web端设为此选项。
powershell代码
  $UserCredential = Get-Credential
  Connect-SPOService -Url https://xxxxx-admin.sharepoint.com -Credential $UserCredential
  Set-SPOTenant -EnableMinimumVersionRequirement $False
web端设置
2.收集&清除历史版本（仅保留最新的一版）.文件多可能需要一段时间来运行
文件说明：
collectHistoryUrls.py  收集所有历史文件链接
delHistoryByeach.py   清除多余历史版本
环境准备：
chromium带user data



#其他
如果你只想清除指定的文件夹历史，推荐使用此脚本来收集，之后执行清除。↓
https://greasyfork.org/zh-CN/scripts/491887-onedrive%E5%8E%BB%E6%96%87%E4%BB%B6%E5%8E%86%E5%8F%B2%E7%89%88%E6%9C%AC-%E5%8D%95%E6%96%87%E4%BB%B6%E5%A4%B9%E7%89%88
