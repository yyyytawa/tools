import os
import sys
import urllib.request
import random
import tempfile
import urllib.parse

user_agents = [
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0);",
    "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1",
    "Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1",
    "Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; en) Presto/2.8.131 Version/11.11",
    "Opera/9.80 (Windows NT 6.1; U; en) Presto/2.8.131 Version/11.11",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Maxthon 2.0)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; TencentTraveler 4.0)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; The World)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SE 2.X MetaSr 1.0; SE 2.X MetaSr 1.0; .NET CLR 2.0.50727; SE 2.X MetaSr 1.0)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; 360SE)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Avant Browser)",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:76.0) Gecko/20100101 Firefox/76.0",
    "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    "Mozilla/5.0 (iPod; U; CPU iPhone OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    "Mozilla/5.0 (iPad; U; CPU OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    "Mozilla/5.0 (Linux; U; Android 2.3.7; en-us; Nexus One Build/FRF91) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    "MQQBrowser/26 Mozilla/5.0 (Linux; U; Android 2.3.7; zh-cn; MB200 Build/GRJ22; CyanogenMod-7) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
    "Opera/9.80 (Android 2.3.4; Linux; Opera Mobi/build-1107180945; U; en-GB) Presto/2.8.149 Version/11.10",
    "Mozilla/5.0 (Linux; U; Android 3.0; en-us; Xoom Build/HRI39) AppleWebKit/534.13 (KHTML, like Gecko) Version/4.0 Safari/534.13",
    "Mozilla/5.0 (BlackBerry; U; BlackBerry 9800; en) AppleWebKit/534.1+ (KHTML, like Gecko) Version/6.0.0.337 Mobile Safari/534.1+",
    "Mozilla/5.0 (hp-tablet; Linux; hpwOS/3.0.0; U; en-US) AppleWebKit/534.6 (KHTML, like Gecko) wOSBrowser/233.70 Safari/534.6 TouchPad/1.0",
    "Mozilla/5.0 (SymbianOS/9.4; Series60/5.0 NokiaN97-1/20.0.019; Profile/MIDP-2.1 Configuration/CLDC-1.1) AppleWebKit/525 (KHTML, like Gecko) BrowserNG/7.1.18124",
    "Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0; HTC; Titan)",
    "UCWEB7.0.2.37/28/999",
    "Openwave/ UCWEB7.0.2.37/28/999",
    "Mozilla/4.0 (compatible; MSIE 6.0; ) Opera/UCWEB7.0.2.37/28/999"
]

randomua = random.choice(user_agents)

def merge_files(files, output_file):
    """合并文件内容到一个输出文件。

    Args:
        files: 要合并的文件列表，可以是本地文件路径或 URL。
        output_file: 输出文件名。
    """
    total_size = 0
    current_size = 0
    global randomua  # 声明全局变量 randomua

    with open(output_file, 'ab') as outfile:
        for i, file in enumerate(files):
            print(f"正在合并文件 {i+1}/{len(files)}: {file}")
            for attempt in range(3):  # 重试 3 次
                try:
                    # 使用 urllib.parse.urlparse 判断 URL 协议类型
                    if urllib.parse.urlparse(file).scheme == 'http' or urllib.parse.urlparse(file).scheme == 'https':
                        # 对 URL 进行解码
                        file = urllib.parse.unquote_plus(file)
                        # 下载 URL 文件
                        request = urllib.request.Request(file, headers={'User-Agent': randomua})  # 使用全局变量 randomua
                        with urllib.request.urlopen(request) as response:
                            data = response.read()
                            outfile.write(data)
                            current_size += len(data)
                            print(f"已合并 {current_size} 字节...", end='\r')
                            break  # 成功下载后退出循环
                    else:
                        # 合并本地文件
                        with open(file, 'rb') as infile:
                            data = infile.read()
                            outfile.write(data)
                            current_size += len(data)
                            print(f"已合并 {current_size} 字节...", end='\r')
                            break  # 成功合并后退出循环
                except urllib.error.URLError as e:
                    print(f"文件 {file} 下载失败: {e}, 正在重试... (尝试 {attempt + 1}/3)")
                    if attempt == 2:  # 如果重试 3 次都失败，则抛出异常
                        raise
                except FileNotFoundError:
                    print(f"文件 {file} 不存在")
                    break  # 文件不存在，退出循环
    print(f"文件已合并到 {output_file}，总大小: {current_size} 字节")

def read_il_file(il_file):
    """读取 il 文件，返回文件内容列表，去除注释。

    Args:
        il_file: il 文件路径

    Returns:
        包含 il 文件内容的列表
    """
    files = []
    with open(il_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or line == '':
                continue
            # 获取链接部分，并去除前后空格
            url = line.split('#')[0].strip()
            # 使用 urllib.parse.quote 对整个 URL 进行编码，并保留 http 和 https
            files.append(urllib.parse.quote(url, safe='http://https:/?=/:'))
    return files

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("使用方法: python merge.py il='文件列表' of='输出文件名' 或 python merge.py if='要合并的文件' of='输出文件名'")
        sys.exit(1)

    # 解析命令行参数
    files = []
    output_file = None
    for arg in sys.argv[1:]:
        if arg.startswith("il="):
            il_file = arg[3:].strip('"')
            # 创建 .cache 目录
            cache_dir = ".cache"
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            # 下载 il.txt 文件到 .cache 目录
            cache_file = os.path.join(cache_dir, "il.txt")
            # 使用 urllib.request 下载 il.txt 文件
            request = urllib.request.Request(il_file, headers={'User-Agent': randomua})  # 使用全局变量 randomua
            with urllib.request.urlopen(request) as response:
                with open(cache_file, 'wb') as f:
                    f.write(response.read())
            files = read_il_file(cache_file)  # 读取 il 文件的内容作为 files 列表
        elif arg.startswith("if="):
            files = arg[3:].strip('"').split(',')
        elif arg.startswith("of="):
            output_file = arg[3:].strip('"')

    if not files or not output_file:
        print("使用方法: python merge.py il='文件列表' of='输出文件名' 或 python merge.py if='要合并的文件' of='输出文件名'")
        sys.exit(1)

    try:
        # 处理 il 文件
        merge_files(files, output_file)
    except Exception as e:
        print(f"文件合并失败: {e}")
