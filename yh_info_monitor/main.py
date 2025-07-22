import json
import requests
import logging
import config
import time
import threading
from datetime import datetime, timedelta
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

monitor_data_file = config.monitor_data_file
token = config.bot_token
lock_data = threading.Lock()
isstarted = False

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
            time.sleep(60)
    else:
        try:
            monitored_list = config.monitored_list
        except Exception as e:
            logging.error(f"无法从配置文件中读取监控列表: {e}")

def load_monitor_data():
    global monitor_data
    try:
        if os.path.exists(monitor_data_file):
            with open(monitor_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    monitor_data = data
                    logging.info(f"监控数据加载成功，共 {len(monitor_data)} 个对象")
                else:
                    monitor_data = {}
                    logging.warning("监控数据文件格式错误,重置为空数据")
        else:
            monitor_data = {}
            logging.info("监控数据文件不存在,创建空数据")
    except Exception as e:
        logging.error(f"加载监控数据失败: {str(e)}")
        monitor_data = {}

def save_monitor_data():
    try:
        with open(monitor_data_file, 'w', encoding='utf-8') as f:
            json.dump(monitor_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存监控数据失败: {str(e)}")

def sync_monitor_data():
    global monitor_data, monitored_list
    keys_to_remove = []
    if not monitored_list: # 禁止空词典执行同步
        return
    with lock_data:
        for id in monitor_data.keys():
            if id not in monitored_list:
                keys_to_remove.append(id)
        if keys_to_remove:
            logging.info(f"有 {len(keys_to_remove)} 个不在被监控列表,准备移除")
            for id in keys_to_remove:
                monitor_data.pop(id,None)
                logging.info(f"{id} 被移除")
                save_monitor_data()
        else:
            return

def get_user_info(user_id):
    api=f"https://chat-web-go.jwzhd.com/v1/user/homepage?userId={user_id}"
    try:
        response = requests.get(api)
        data = response.json()
        if data.get("code") == 1 and data.get("data") and data.get("data").get("user"):
            user_info = data["data"]["user"]
            return {
              "nickname": user_info.get("nickname", ""),
              "avatarUrl": user_info.get("avatarUrl", "")
            }
            
        elif data.get("code") != 1:
            logging.error(f"错误, 返回码 {data.get('code')}")
            return None
        else:
            logging.error("API错误")
            return None
        
    except Exception as e:
        logging.error(f"发生错误: {e}")
        return None

def push_msg(id,type,content,contenttype): # 发送消息的函数
    global token
    try:
        payload = json.dumps({
            "recvId": str(id),
            "recvType": type,
            "contentType": contenttype,
            "content": { 
                "text": content
            }
        })  
        headers = {
          'Content-Type': 'application/json; charset=utf-8'
        }
        response = requests.post(f"https://chat-go.jwzhd.com/open-apis/v1/bot/send?token={token}",headers=headers,data=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 1:
            logging.info("发送成功")
        else:
            logging.error(f"发送失败,服务端返回: {data.get('code')}, msg: {data.get('msg')}")
    except Exception as e:
        logging.error(f"错误: {e}")

def make_html(id,old_name,new_name,old_avatar,new_avatar):
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if new_name != old_name:
        name_part = f"""
    <div style="margin-bottom: 12px;">
        <span style="font-weight: bold; color: #586069;">名称变化:</span>
        <span style="color: #24292e;">{old_name} → {new_name}</span>
    </div>
        """
    else:
        name_part = f"""  
    <div style="margin-bottom: 12px;">
        <span style="font-weight: bold; color: #586069;">当前名称:</span>
        <span style="color: #24292e;">{old_name}</span>
    </div>
         """
    if new_avatar != old_avatar:
        avatar_part = f"""
        <div style="margin-bottom: 16px;">
        <div style="font-weight: bold; color: #586069; margin-bottom: 4px;">头像更新:</div>
        <div style="display: flex; gap: 16px; align-items: center;">
            <div>
                <div style="font-size: 13px; color: #586069; margin-bottom: 4px;">原头像</div>
                <img src="{old_avatar}" style="width: 50px; height: 50px; border-radius: 4px; border: 1px solid #e1e4e8;">
            </div>
            <div style="font-size: 20px; color: #586069;">→</div>
            <div>
                <div style="font-size: 13px; color: #586069; margin-bottom: 4px;">新头像</div>
                <img src="{new_avatar}" style="width: 50px; height: 50px; border-radius: 4px; border: 1px solid #e1e4e8;">
            </div>
        </div>
    </div>
        """
    else:
        avatar_part = f"""
    <div style="margin-bottom: 16px;">
        <div style="font-weight: bold; color: #586069; margin-bottom: 4px;">目前头像:</div>
        <img src="{old_avatar}" style="width: 50px; height: 50px; border-radius: 4px; border: 1px solid #e1e4e8;">
    </div>
        """
    html_content = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e1e4e8; border-radius: 6px; padding: 16px; background-color: #f6f8fa;">
    <h2 style="color: #24292e; margin-top: 0; border-bottom: 1px solid #e1e4e8; padding-bottom: 8px;">监控信息更新</h2>
    
    <div style="margin-bottom: 12px;">
        <span style="font-weight: bold; color: #586069;">ID:</span>
        <span style="color: #24292e;">{id}</span>
    </div>
    {name_part}
    {avatar_part}
    <div style="font-size: 12px; color: #586069; text-align: right; border-top: 1px solid #e1e4e8; padding-top: 8px;">
        更新时间: {update_time}
    </div>
</div>"""
    return html_content

def monitor_thread_instance():
    global monitor_data, monitored_list
    logging.info("监控线程开始启动")
    while True:
        try:
            list_to_check = list(monitored_list.keys())
            logging.info(f"开启本轮检查,共 {len(list_to_check)} 个对象")
            for user_id in monitored_list:
                old_user_info = monitor_data.get(user_id, {})
                logging.info(f"正在获取 {user_id} 信息")
                current_info = get_user_info(user_id)
                if not current_info:
                    logging.error(f"无法获取用户 {user_id} 信息,跳过")
                    continue
                
                if not old_user_info:
                    logging.info(f"首次记录用户 {user_id} 的信息。")
                    with lock_data:
                        monitor_data[user_id] = {
                            "nickname": current_info["nickname"],
                            "avatarUrl": current_info["avatarUrl"],
                        }
                    save_monitor_data()
                    time.sleep(10)
                    continue

                nickname_changed = current_info.get("nickname") != old_user_info.get("nickname")
                avatar_changed = current_info.get("avatarUrl") != old_user_info.get("avatarUrl")
                changed = nickname_changed or avatar_changed
                
                if changed:
                    msg_content = make_html(
                        user_id,
                        old_user_info.get("nickname"),
                        current_info.get("nickname"),
                        old_user_info.get("avatarUrl"),
                        current_info.get("avatarUrl")
                    )

                    for notify_group in monitored_list.get(user_id).get("group",""):
                        push_msg(notify_group,"group",msg_content,"html")
                        logging.info(f"推送 {user_id} 信息到群组 {notify_group}")
                        time.sleep(1)
                    for notify_user in monitored_list.get(user_id).get("user",""):
                        push_msg(notify_user,"user",msg_content,"html")
                        logging.info(f"推送 {user_id} 信息到用户 {notify_user}")
                        time.sleep(1)
                        
                    with lock_data:
                        monitor_data[user_id]["nickname"] = current_info["nickname"]
                        monitor_data[user_id]["avatarUrl"] = current_info["avatarUrl"]
                    save_monitor_data()
                else:
                    logging.info(f"{user_id} 信息无变化")
                time.sleep(10) # 每个用户间隔

            logging.info("本轮用户检查完成")
            time.sleep(10) # 每次检查间隔
                
        except Exception as e:
            logging.error(f"监控线程出错: {str(e)}")
            time.sleep(10)

def start_monitor_thread():
    global isstarted
    if isstarted:
        logging.info("监控线程已经启动，跳过")
        return
    load_monitored_list()
    load_monitor_data()
    monitor_thread = threading.Thread(target=monitor_thread_instance, daemon=True)
    monitor_thread.start()
    isstarted = True
    logging.info("用户监控线程已经启动")

if __name__ == "__main__":
    start_monitor_thread()
    
    try: # 论server作用
        while True:
            load_monitored_list()
            sync_monitor_data()
            time.sleep(3600)
    except KeyboardInterrupt:
        logging.info("程序被终止。")
    except Exception as e:
        logging.error(f"主线程异常: {e}")