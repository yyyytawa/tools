import json
import tomllib as toml
from html import escape as html_escape
import httpx
import logging
import config
import time
import threading
import asyncio
from mod.ws import ws
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO,
 format='%(asctime)s - %(levelname)s - %(message)s', filename = config.log_file, filemode="w")

httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

time_per_object = config.time_per_object
time_per_check = config.time_per_check
time_per_push = config.time_per_push
monitor_data_file = config.monitor_data_file
user_token = config.user_token
last_active_info = {}
token = config.bot_token
lock_data = threading.Lock()
isstarted = False

def load_monitored_list():
    global monitored_list
    if config.monitored_list_url != "":
        try:
            response = httpx.get(config.monitored_list_url)
            response.raise_for_status()
            monitored_list = toml.loads(response.text)
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
        response = httpx.get(api)
        data = response.json()
        if data.get("code") == 1 and data.get("data") and data.get("data").get("user"):
            user_info = data["data"]["user"]
            return {
              "name": user_info.get("nickname", ""), # byd机器人和用户nickname,群聊name.
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

def get_group_info(group_id):
    api = "https://chat-web-go.jwzhd.com/v1/group/group-info"
    try:
        post_data = {"groupId": str(group_id)}
        response = httpx.post(api, json = post_data)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 1 and data.get("data"):
            group_info = data["data"]["group"]
            return {
              "name": group_info.get("name",""),
              "avatarUrl": group_info.get("avatarUrl",""),
              "introduction": group_info.get("introduction","")
            }
        elif data.get("code") != 1:
            logging.error(f"服务端返回错误码: {data.get("code")},msg: {data.get("msg")}")
            return None
        else:
            logging.error("API请求错误")
            return None

    except Exception as e:
        logging.error(f"获取群聊信息失败: {e}")
        return None

def get_bot_info(bot_id):
    api = "https://chat-web-go.jwzhd.com/v1/bot/bot-info"
    try:
        post_data = {"botId": str(bot_id) }
        response = httpx.post(api, json = post_data)
        logging.debug(response)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 1 and data.get("data"):
            bot_info = data["data"]["bot"]
            return {
              "name": bot_info.get("nickname",""),
              "avatarUrl": bot_info.get("avatarUrl",""),
              "introduction": bot_info.get("introduction","")
            }
              
        elif data.get("code") != 1:
            logging.error(f"服务端返回错误码: {data.get("code")} msg: {data.get("msg")}")
            return
        else:
            logging.error("API错误")
            return
    except Exception as e:
        logging.error(f"获取机器人信息失败: {e}")
        return

def push_msg(id,type,content,contenttype): # 发送消息的函数
    global token
    try:
        payload = {
            "recvIds": id,
            "recvType": type,
            "contentType": contenttype,
            "content": { 
                "text": content
            }
        }
        headers = {
          'Content-Type': 'application/json; charset=utf-8'
        }
        response = httpx.post(f"https://chat-go.jwzhd.com/open-apis/v1/bot/batch_send?token={token}",headers=headers, json = payload)
        response.raise_for_status()
        data = response.json()
        if data.get("code") == 1:
            logging.info(f"推送消息给{len(id)}个对象,成功{data.get("data").get("successCount")}个对象,失败{len(id)-data.get("data").get("successCount")}个,")
            logging.debug(f"{data}")
        else:
            logging.error(f"发送失败,服务端返回: {data.get('code')}, msg: {data.get('msg')}")
    except Exception as e:
        logging.error(f"错误: {e}")

def make_html(id,type,old_name,new_name,old_avatar,new_avatar,old_introduction, new_introduction, *update_time):
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    type_mapping = {
        "user": "用户",
        "group": "群聊",
        "bot": "机器人"
    }
    type_text = type_mapping.get(type)
    if not type_text:
        logging.error(f"未知类型: {type}")
        type_text = ""

    old_name = html_escape(old_name) # 转义防注入
    new_name = html_escape(new_name)
    old_avatar = html_escape(old_avatar)
    new_avatar = html_escape(new_avatar)
    old_introduction = html_escape(old_introduction)
    new_introduction = html_escape(new_introduction)

    if new_name != old_name: # 名称
        name_part = f"""
    <div style="margin-bottom: 12px;">
        <span style="font-weight: bold; color: #586069;">{type_text}名称变化:</span>
        <span style="color: #24292e;">{old_name} → {new_name}</span>
    </div>
        """
    else:
        name_part = f"""  
    <div style="margin-bottom: 12px;">
        <span style="font-weight: bold; color: #586069;">{type_text}当前名称:</span>
        <span style="color: #24292e;">{old_name}</span>
    </div>
         """

    if new_avatar != old_avatar: # 头像
        avatar_part = f"""
        <div style="margin-bottom: 16px;">
        <div style="font-weight: bold; color: #586069; margin-bottom: 4px;">{type_text}头像更新:</div>
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
        <div style="font-weight: bold; color: #586069; margin-bottom: 4px;">{type_text}目前头像:</div>
        <img src="{old_avatar}" style="width: 50px; height: 50px; border-radius: 4px; border: 1px solid #e1e4e8;">
    </div>
        """

    if (type == "group" or type == "bot") and new_introduction != old_introduction: # 简介
        introduction_part = f"""
    <div style="margin-bottom: 16px;">
        <div style="font-weight: bold; color: #586069; margin-bottom: 8px;">{type_text}简介变化:</div>
        <div style="background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 4px; padding: 12px; margin-bottom: 8px;">
            <div style="font-size: 13px; color: #586069; margin-bottom: 4px;">原简介:</div>
            <div style="color: #24292e; line-height: 1.4;">{old_introduction}</div>
        </div>
        <div style="text-align: center; margin: 8px 0;">
            <div style="font-size: 16px; color: #586069;">↓</div>
        </div>
        <div style="background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 4px; padding: 12px;">
            <div style="font-size: 13px; color: #586069; margin-bottom: 4px;">新简介:</div>
            <div style="color: #24292e; line-height: 1.4;">{new_introduction}</div>
        </div>
    </div>
        """
    elif (type == "group" or type == "user") and old_introduction != "" and new_introduction == old_introduction:
        introduction_part =f"""
    <div style="margin-bottom: 16px;">
        <div style="font-weight: bold; color: #586069; margin-bottom: 8px;">当前简介:</div>
        <div style="background-color: #ffffff; border: 1px solid #e1e4e8; border-radius: 4px; padding: 12px;">
            <div style="color: #24292e; line-height: 1.4;">{old_introduction}</div>
        </div>
    </div>
    """
    else:
        introduction_part = ""

    html_content = f"""<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e1e4e8; border-radius: 6px; padding: 16px; background-color: #f6f8fa;">
    <h2 style="color: #24292e; margin-top: 0; border-bottom: 1px solid #e1e4e8; padding-bottom: 8px;">{type_text}信息更新</h2>
    
    <div style="margin-bottom: 12px;">
        <span style="font-weight: bold; color: #586069;">{type_text}ID:</span>
        <span style="color: #24292e;">{id}</span>
    </div>
    {name_part}
    {avatar_part}
    {introduction_part}
    <div style="font-size: 12px; color: #586069; text-align: right; border-top: 1px solid #e1e4e8; padding-top: 8px;">
        更新时间: {update_time}
    </div>
</div>"""
    return html_content

def make_md(old_avatar, new_avatar): # ~~等后续Feng修HTML访问云湖图床bug后删除~~ 代码二次利用
    if old_avatar == new_avatar:
        content =f"```Now_avatar \n{new_avatar}\n```"
    else:
        content =f"```New_avatar \n{new_avatar}\n```\n```Old_avatar\n{old_avatar}\n```"
    return content

def notify(id: list, type: str, old_name: str, new_name: str, old_avatar: str, new_avatar: str, old_introduction: str, new_introduction: str, notify_user = [], notify_group = []):
    msg_content = make_html(
        id,
        type = type,
        old_name = old_name,
        new_name = new_name,
        old_avatar = old_avatar,
        new_avatar = new_avatar,
        old_introduction = old_introduction,
        new_introduction = new_introduction
        )
                    
    msg_content_md = make_md( # ~~等后续Feng修HTML访问云湖图床bug后删除~~ 代码复用啦啦啦🌶️~
        old_avatar = old_avatar,
        new_avatar = new_avatar
    )

    if notify_group:
        push_msg(notify_group,"group",msg_content,"html")
        push_msg(notify_group,"group",msg_content_md,"markdown") # ~~等后续Feng修HTML访问云湖图床bug后删除~~ 代码二次利用x2
        logging.info(f"推送 {id} 信息到群组 {notify_group}")
        time.sleep(time_per_push)
    if notify_user:
        push_msg(notify_user,"user",msg_content,"html")
        push_msg(notify_user,"user",msg_content_md,"markdown") # ~~等后续Feng修HTML访问云湖图床bug后删除~~ 代码二次利用x3
        logging.info(f"推送 {id} 信息到用户 {notify_user}")

def monitor_thread_instance():
    global monitor_data, monitored_list, time_per_check, time_per_object, time_per_push, last_active_info
    logging.info("监控线程开始启动")
    while True:
        try:
            list_to_check = list(monitored_list.keys())
            logging.info(f"开启本轮检查,共 {len(list_to_check)} 个对象")
            for id in monitored_list:
                if time.time()-last_active_info.get(id,0) < 3600:
                    logging.info(f"对象 {id} 在最近1h内活跃过,跳过")
                    time.sleep(time_per_object/10)
                    continue
                start_time = time.time()
                old_info = monitor_data.get(id, {}).copy()

                type = monitored_list.get(id).get("type","user")
                if type == "user":
                    current_info = get_user_info(id)
                    type_text = "用户"
                elif type == "group":
                    current_info = get_group_info(id)
                    type_text = "群聊"
                elif type == "bot":
                    current_info = get_bot_info(id)
                    type_text = "机器人"
                else:
                    logging.error(f"未知类型: {type}")
                    type_text = "未知"

                logging.info(f"正在获取{type_text}: {id} 信息")
                if not current_info:
                    logging.error(f"无法获取{type_text}: {id} 信息,跳过")
                    continue
                
                if not old_info:
                    logging.info(f"首次记录{type_text}: {id} 的信息")
                    with lock_data:
                        monitor_data[id] = {
                            "name": current_info["name"],
                            "avatarUrl": current_info["avatarUrl"],
                            "introduction": current_info.get("introduction","")
                        }
                    save_monitor_data()
                    time.sleep(time_per_object)
                    continue

                name_changed = current_info.get("name") != old_info.get("name")
                avatar_changed = current_info.get("avatarUrl") != old_info.get("avatarUrl")
                introduction_changed = current_info.get("introduction","") != old_info.get("introduction","")
                changed = name_changed or avatar_changed or introduction_changed
                
                if changed:
                    if not start_time > last_active_info.get(id, 0):   # 加个检测防止和ws的重复推送
                        logging.info(f"对象 {id} 的信息变化可能被WS推送过,跳过")
                        time.sleep(time_per_object/10)
                        continue
                    with lock_data:
                        monitor_data[id]["name"] = current_info["name"]
                        monitor_data[id]["avatarUrl"] = current_info["avatarUrl"]
                        monitor_data[id]["introduction"] = current_info.get("introduction","")
                    save_monitor_data()

                    notify(id = id,
                          type = type,
                          old_name = old_info.get("name"),
                          new_name = current_info.get("name"),
                          old_avatar = old_info.get("avatarUrl"),
                          new_avatar = current_info.get("avatarUrl"),
                          old_introduction = old_info.get("introduction",""),
                          new_introduction = current_info.get("introduction",""),
                          notify_group = monitored_list.get(id).get("group",[]),
                          notify_user = monitored_list.get(id).get("user",[]))
                else:
                    logging.info(f"{type_text}: {id} 信息无变化")
                time.sleep(time_per_object)

            logging.info("本轮检查完成")
            time.sleep(time_per_check) # 每次检查间隔
                
        except Exception as e:
            logging.error(f"监控线程出错: {str(e)}")
            time.sleep(10)

def monitor_thread_instance_ws():
    logging.info("开启WS检测线程")
    while True:
        try:
            asyncio.run(monitor_async_ws())
        except Exception as e:
            logging.error(f"WS线程发生错误 {e}")

async def monitor_async_ws():
    global user_token, last_active_info, monitor_data, monitored_list
    ws_client = ws(user_token)
    async for data in ws_client.connect(mode = "white", list =["push_message"]):
        msg = data["data"]["msg"]
        if not msg.get("sender",{}).get("chatId"):
            logging.info("WS: 无法获取到发送者的chatId,跳过")
            continue

        sender_info = msg["sender"]
        if sender_info.get("chatId") not in monitored_list:
            logging.info(f"WS: 对象 {sender_info.get('chatId')} 不在被监控列表中,跳过")
            continue

        last_active_info[sender_info["chatId"]] = int(msg["timestamp"])/1000
        logging.debug(last_active_info)
        old_info = monitor_data.get(sender_info["chatId"], {}).copy()
        if not old_info:
            logging.info(f"WS: 首次记录对象 {sender_info['chatId']} 的信息")
            with lock_data:
                monitor_data[sender_info["chatId"]] = {
                    "name": sender_info.get("name"),
                    "avatarUrl": sender_info.get("avatarUrl"),
                    "introduction": ""
                }
            save_monitor_data()
            continue

        name_changed = sender_info.get("name") != old_info.get("name")
        avatar_changed = sender_info.get("avatarUrl") != old_info.get("avatarUrl")
        changed = name_changed or avatar_changed
        if changed:
            logging.info(f"对象 {sender_info['chatId']} 信息发生变化,准备推送,相关msg_id: {msg['msgId']}")
            logging.info(old_info)
            logging.info(sender_info)
            with lock_data:
                monitor_data[sender_info["chatId"]]["name"] = sender_info.get("name")
                monitor_data[sender_info["chatId"]]["avatarUrl"] = sender_info.get("avatarUrl")
            save_monitor_data()

            notify(id = sender_info["chatId"],
                  type = monitored_list.get(sender_info["chatId"], {}).get("type", "user"),
                  old_name = old_info.get("name"),
                  new_name = sender_info.get("name"),
                  old_avatar = old_info.get("avatarUrl"),
                  new_avatar = sender_info.get("avatarUrl"),
                  old_introduction = old_info.get("introduction",""),
                  new_introduction = old_info.get("introduction",""),
                  notify_group = monitored_list.get(sender_info["chatId"]).get("group",[]),
                  notify_user = monitored_list.get(sender_info["chatId"]).get("user",[]))
        else:
            logging.info(f"WS: 对象 {sender_info.get("chatId")} 信息无变化")

def start_monitor_thread():
    global isstarted
    if isstarted:
        logging.info("监控线程已经启动，跳过")
        return
    load_monitored_list()
    load_monitor_data()
    if user_token:
        monitor_thread_ws = threading.Thread(target=monitor_thread_instance_ws, daemon=True)
        monitor_thread_ws.start()
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
        logging.info("程序被终止")
    except Exception as e:
        logging.error(f"主线程异常: {e}")