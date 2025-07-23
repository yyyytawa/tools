bot_token = "gtdcngdhjfdbd"    # BOT TOKEN
# 监控列表与监控数据相关
monitored_list = { # 不需要可留空
  "6301414": {
    "type": "user",
    "user": [7354488],
  },
  "875050655": {
    "type": "group",
    "group": [257731539]
  },
  "34433153": {
    "type": "bot",
    "user": [7354488],
    "group": [257731539]
  }
}
monitor_data_file = "monitor_data.json"
monitored_list_url = "" # 填写被监控名单URL
# 等待时长相关
time_per_object = 10 # 每两个检测对象等待时长
time_per_check = 10 # 每两轮检测等待时长
time_per_push = 1 # 每两次推送的等待时间
# 日志相关
log_file = "" # 日志文件名称,留空不保存日志文件,开启此项会导致控制台无输出,不推荐开启因为我没做日志大小限制和分割(