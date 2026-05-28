#  Copyright © [2024] 程序那些事
#
#  All rights reserved. This software and associated documentation files (the "Software") are provided for personal and educational use only. Commercial use of the Software is strictly prohibited unless explicit permission is obtained from the author.
#
#  Permission is hereby granted to any person to use, copy, and modify the Software for non-commercial purposes, provided that the following conditions are met:
#
#  1. The original copyright notice and this permission notice must be included in all copies or substantial portions of the Software.
#  2. Modifications, if any, must retain the original copyright information and must not imply that the modified version is an official version of the Software.
#  3. Any distribution of the Software or its modifications must retain the original copyright notice and include this permission notice.
#
#  For commercial use, including but not limited to selling, distributing, or using the Software as part of any commercial product or service, you must obtain explicit authorization from the author.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHOR OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#  Author: 程序那些事
#  email: flydean@163.com
#  Website: [www.flydean.com](http://www.flydean.com)
#  GitHub: [https://github.com/ddean2009/MoneyPrinterPlus](https://github.com/ddean2009/MoneyPrinterPlus)
#
#  All rights reserved.
#
#

import subprocess
import time
import os
import sys

import selenium
from selenium import webdriver

from tools.utils import get_must_session_option


def get_chrome_path():
    """获取 Chrome 可执行文件路径"""
    # 常见的 Chrome 安装路径
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            return path
    return None


def is_chrome_debug_running(debug_port="9222"):
    """检查 Chrome 调试模式是否正在运行"""
    try:
        import urllib.request
        url = f"http://127.0.0.1:{debug_port}/json"
        urllib.request.urlopen(url, timeout=1)
        return True
    except:
        return False


def start_chrome_debug_mode(debug_port="9222", user_data_dir=None):
    """启动 Chrome 调试模式"""
    chrome_path = get_chrome_path()
    if not chrome_path:
        raise Exception("找不到 Chrome 浏览器，请确保已安装 Chrome")

    # 构建 Chrome 启动命令
    cmd = [chrome_path, f"--remote-debugging-port={debug_port}"]

    # 如果指定了用户数据目录
    if user_data_dir:
        cmd.append(f"--user-data-dir={user_data_dir}")
    else:
        # 使用临时用户数据目录避免冲突
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_debug_data")
        cmd.append(f"--user-data-dir={temp_dir}")

    # 启动 Chrome
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Chrome 调试模式已启动，端口: {debug_port}")
        # 等待 Chrome 启动
        time.sleep(2)
        return True
    except Exception as e:
        print(f"启动 Chrome 失败: {e}")
        return False


def init_driver():
    driver_type = get_must_session_option('video_publish_driver_type', "请设置驱动类型")
    driver_location = get_must_session_option('video_publish_driver_location', "请设置驱动位置")
    debugger_address = get_must_session_option('video_publish_debugger_address', "请设置debugger地址")
    if driver_type == 'chrome':
        # 检查是否需要自动启动 Chrome
        auto_start = st.session_state.get('video_publish_auto_start_chrome', False) if 'st' in sys.modules else False
        debug_port = debugger_address.split(':')[1] if ':' in debugger_address else '9222'

        if not is_chrome_debug_running(debug_port):
            print(f"Chrome 调试模式未运行，自动启动中...")
            if not start_chrome_debug_mode(debug_port):
                raise Exception("无法自动启动 Chrome，请手动启动 Chrome 后重试")

        # 启动浏览器驱动服务
        service = selenium.webdriver.chrome.service.Service(driver_location)
        # Chrome 的调试地址
        debugger_address = debugger_address
        # 创建Chrome选项，重用现有的浏览器实例
        options = selenium.webdriver.chrome.options.Options()
        options.page_load_strategy = 'normal'  # 设置页面加载策略为'normal' 默认值, 等待所有资源下载,
        options.add_experimental_option('debuggerAddress', debugger_address)
        # 使用服务和选项初始化WebDriver
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)  # 设置隐式等待时间为15秒
        return driver
    elif driver_type == 'firefox':
        # 启动浏览器驱动服务
        service = selenium.webdriver.firefox.service.Service(driver_location,
                                                             service_args=['--marionette-port', '2828',
                                                                           '--connect-existing'])
        # 创建firefox选项，重用现有的浏览器实例
        options = selenium.webdriver.firefox.options.Options()
        options.page_load_strategy = 'normal'  # 设置页面加载策略为'normal' 默认值, 等待所有资源下载,
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(10)  # 设置隐式等待时间为15秒
        return driver
