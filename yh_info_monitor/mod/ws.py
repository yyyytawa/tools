from . import chat_ws_go_pb2 as ws_pb2
import websockets
import uuid
import httpx
import logging
import asyncio
import json

class ws:
    def __init__(self, token, user_id = None, platform = "windows", deviceId = uuid.uuid4().hex):
        if not user_id:
            client = web.user(token)
            response = client.info()
            if response.get("code") != 1:
                logging.error(f"请求出错, msg: {response.get("msg")}")
                return

            user_id = response["data"]["user"]["userId"]

        self.token = token
        self.user_id = user_id
        self.platform = platform
        self.deviceId = deviceId
        self.ws = None
        self.enable = True

    async def heartbeat_ack(self): # 发送心跳包的协程
        while self.enable:
            try:
                heartbeat = json.dumps({
                    "seq": uuid.uuid4().hex,
                    "cmd": "heartbeat",
                    "data": {}
                })
                logging.debug("正在发送心跳包")
                await self.ws.send(heartbeat)
                await asyncio.sleep(30)
            except websockets.exceptions.ConnectionClosed:
                logging.debug("退出心跳协程")
                break
            except asyncio.CancelledError:
                logging.info("退出心跳协程")
                raise
            except Exception as e:
                logging.error(e)
                break
    
    async def connect(self, decode = True, mode = "black", list = []): # 连接到WS的
        self.enable = True
        while self.enable:
            try:
                api = "wss://chat-ws-go.jwzhd.com/ws"
                async with websockets.connect(api) as self.ws:
                    login = json.dumps({
                      "seq": uuid.uuid4().hex,
                      "cmd": "login",
                      "data": {
                        "userId": self.user_id,
                        "token": self.token,
                        "platform": self.platform,
                        "deviceId": self.deviceId
                      }
                    })
                    logging.info("正在发送登录请求")
                    await self.ws.send(login)
                    heartbeat_task = asyncio.create_task(self.heartbeat_ack())
                    if not decode:
                        while self.enable:
                            response = await asyncio.wait_for(self.ws.recv(),timeout = 70)
                            logging.debug(response.hex())
                            yield response
                    else:
                        while self.enable:
                            response = await asyncio.wait_for(self.ws.recv(),timeout = 70)
                            logging.debug(response.hex())
                            msg = await self.decode(response, mode = mode, list = list)
                            if msg:
                                yield msg
                            else:
                                continue
            except websockets.exceptions.ConnectionClosed:
                logging.error("WS断开")
                if heartbeat_task:
                    heartbeat_task.cancel()
            except asyncio.TimeoutError:
                if self.ws:
                    await self.ws.close()
                if heartbeat_task:
                    heartbeat_task.cancel()
                logging.error("服务端过长时间未发送消息,尝试重连中")
            except Exception as e:
                logging.error(e)
                if heartbeat_task:
                    heartbeat_task.cancel()
                await asyncio.sleep(5)
            finally:
                if heartbeat_task:
                    heartbeat_task.cancel()
    
    async def close(self):
        self.enable = False
        if self.ws:
          await self.ws.close()
          self.ws = None

    async def decode(self, msg, mode = "black", list = []):
        from google.protobuf import json_format
        cmd_map = {
            "draft_input": ws_pb2.draft_input,
            "push_message": ws_pb2.push_message,
            "edit_message": ws_pb2.edit_message,
            "file_send_message": ws_pb2.edit_message
        }
        msg_temp = ws_pb2.heartbeat_ack()
        msg_temp.ParseFromString(msg)

        if mode == "black" and msg_temp.info.cmd in list:
            return
        elif mode == "white" and msg_temp.info.cmd not in list:
            return

        if msg_temp.info.cmd == "heartbeat_ack":
            msg_data = json_format.MessageToDict(msg_temp)
            return msg_data  
        elif msg_temp.info.cmd in cmd_map:
            msg_class = cmd_map[msg_temp.info.cmd]
            msg_data = msg_class()
            msg_data.ParseFromString(msg)
            msg_data = json_format.MessageToDict(msg_data)
            return msg_data
        else:
            logging.warn(f"暂时不支持反序列化 {msg_temp.info.cmd}")

class web:
    """chat-web-go 相关的请求"""
    def __init__(self, token = None):
        self.token = token
        self.user = self.user(token)

    class user:
        """user路由下的请求"""
        def __init__(self, token):
            self.token = token
        
        def request_api_get(self, url, headers = None):
            with httpx.Client(transport = httpx.HTTPTransport(retries = 3)) as client:
                response = client.get(f"https://chat-web-go.jwzhd.com/v1/user/{url}", headers = headers)
                response.raise_for_status()
            return response.json()

        def info(self):
            headers = {"token": self.token}
            response = self.request_api_get("info", headers = headers)
            return response