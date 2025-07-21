import json
import requests
import logging
import config
import sys
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

monitor_data_file = config.monitor_data_file
token = config.bot_token

def load_monitored_list():
    global monitored_list
    if config.monitored_list_url != "":
        try:
            data = requests.get(config.monitored_list_url)
            data.raise_for_status()
            monitored_list = data.json()
            logging.info("从网络获取监控列表成功")
        
        except Exception as e:
            logging.error(f"从网络获取监控列表失败: {e}")
    else:
        try:
            monitored_list = config.monitored_list
        except Exception as e:
            logging.error(f"无法从配置文件中读取监控列表: {e}")
            sys.exit(1)

def load_monitor_data():
    global monitor_data
    try:
        if os.path.exists(monitor_data_file):
            with open(monitor_data_file, 'r', encoding='utf-8') as f:
                monitor_data = json.load(f)
                logging.info(f"用户数据加载成功，共 {len(monitor_data)} 个用户")
        else:
            monitor_data = {}
            logging.info("用户数据文件不存在，已创建空数据")
    except Exception as e:
        logging.error(f"加载用户数据失败: {str(e)}")
        monitor_data = {}

def save_monitor_data():
    try:
        with open(monitor_data_file, 'w', encoding='utf-8') as f:
            json.dump(monitor_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存用户数据失败: {str(e)}")

def get_user_info(user_id):
    api=f"https://chat-web-go.jwzhd.com/v1/user/homepage?userId={user_id}"
    try:
        response = requests.get(api)
        data = response.json()
        if data.get("code") == 1 and data.get("data").get("user"):
        user_info = data["data"]["user"]
            return {
              "nickname": user_info.get("nickname", ""),
              "avatarUrl": user_info.get("avatarUrl", "")
            }
            
        elif data.get("code") != 1:
            logging.error(f"错误, 返回码 {data.get('code')")
        else:
            logging.error("API错误")
        
    except Exception as e:
        logging.error(f"发生错误: {e})

def push_msg(id,type,content,contenttype): # 发送消息的函数
    try:
        payload = json.dumps({
            "recvId": id,
            "recvType": type,
            "contentType": contenttype,
            "content": {
                content
            }
        })  
        headers = {
          'Content-Type': 'application/json'
        }
        response = requests.post(f"https://chat-go.jwzhd.com/open-apis/v1/bot/send?token={token}",headers=headers,data=payload)
        response.raise_for_status()
        data = response.json()
        if data.get["code"] == 1:
            logging.info("发送成功")
        else:
            logging.error(f"发送失败,服务端返回: {data.get['code']}, msg: data.get['msg']")
    except Exception as e:
        logging.error(f"错误: {e}")
