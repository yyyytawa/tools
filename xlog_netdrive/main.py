import httpx
import os
import logging
import json
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置区域
prefix = "https://ipfs.crossbell.io/ipfs/" # 注意最后带"/"
default_file_name = "file.bin" # 默认文件名
chunk_size = 6 * 1024 * 1024 #分片大小

# 参数
parser = argparse.ArgumentParser(description="xlog网盘")

group = parser.add_mutually_exclusive_group(required=True)

# 互斥参数
group.add_argument("-u", "--upload_file", type=str,default=None, help="上传文件") # 位置参数
parser.add_argument("-f", "--file_path", type=str, default=default_file_name, help="保存文件位置(可选)")
parser.add_argument("-n", "--file_name", type=str, default=None, help="文件名称(可选)")
group.add_argument("-d", "--download_file", type=str,default=None, help="输入取件码")

# 解析参数
args = parser.parse_args()

def download_file(url_list: list[str],file_path: str, prefix=prefix):
    try:
        with httpx.Client(http2=True, follow_redirects=True, timeout=30) as client:
            with open(file_path,"ab") as f:
                for url in url_list:
                    try:
                        with client.stream("GET",prefix+url) as response:
                            response.raise_for_status()
                            logging.debug(f"状态码: {response.status_code}")
                            for chunk in response.iter_bytes():
                                f.write(chunk)
                                logging.debug(f"写入 {url} 的分块")
                    except httpx.HTTPStatusError as e:
                        logging.error(f"  URL '{url}' 请求错误: 状态码 {e.response.status_code} - {e.response.text}")
                    except httpx.RequestError as e:
                        logging.error(f"  URL '{url}' 请求失败: {e}")
                    except Exception as e:
                        logging.error(f"  URL '{url}' 发生未知错误: {e}")
    except Exception as e:
        logging.error(f"发生错误 {e}")

def spilt_file(file_path,chunk_size):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件未找到: {file_path}")
        return
    if not os.path.isfile(file_path):
        raise ValueError(f"路径 '{file_path}' 不是一个有效的文件。")
        return
    try:
        with open(file_path,"rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk: # 检测是否上传完成
                    break
                yield chunk
    except Exception as e:
        logging.error(f"发生错误 {e}")

def upload_file(file_path, chunk_size):
    file_list = []
    for chunk_data in spilt_file(file_path, chunk_size):
        try:
            upload_url = "https://ipfs-relay.crossbell.io/upload"
            files = {'file': chunk_data}
            response = httpx.post(upload_url,files=files)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "ok":
                logging.error(f"错误: {response}")
                return
            file_list.append(data.get("cid"))
        except Exception as e:
            logging.error(f"发生错误 {e}")
    return file_list

def make_meta_file(url_list, name=None):
    meta_file = {
        "name": name,
        "cid": url_list
    }
    return meta_file

def upload_meta_file(content):
    try:
        upload_url = "https://ipfs-relay.crossbell.io/upload"
        files = {'file': json.dumps(content).encode('utf-8')}
        response = httpx.post(upload_url, files=files)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "ok":
            logging.error(f"错误: {response}")
            return
        return data.get("cid")
    except Exception as e:
        logging.error(f"发生错误 {e}")
        return

def get_info(cid,prefix=prefix):
    try:
       response = httpx.get(prefix+cid)
       response.raise_for_status()
       data = response.json()
       return {
           "name": data.get("name",default_file_name),
           "cid": data.get("cid",[])
       }
    except Exception as e:
        logging.error(f"发生错误 {e}")
        return

if __name__ == "__main__":
    if args.upload_file !=None:
        url_list = upload_file(args.upload_file,chunk_size)
        if url_list:
            meta_file = make_meta_file(name=args.file_name,url_list = url_list)
            cid = upload_meta_file(meta_file)
            logging.info(f"取件码: {cid}")
        else:
            logging.error("上传出错")
    if args.download_file != None:
        meta_info = get_info(args.download_file)
        if meta_info:
            logging.info("正在下载文件")
            if args.file_path == default_file_name and meta_info.get("name") != None:
                file_path = meta_info.get("name",default_file_name).replace("/","_").replace("\\","_")
            else:
                file_path = args.file_path
            download_file(file_path = file_path, url_list = meta_info.get("cid"))
        else:
            logging.error("无法获取文件信息")