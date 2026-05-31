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

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import streamlit as st
import pyperclip
import sys
from selenium.webdriver import Keys

import time

from config.config import xiaohongshu_site
from tools.file_utils import read_head, read_file_with_extra_enter, read_file_start_with_secondline


def xiaohongshu_publisher(driver, video_file, text_file, **kwargs):
    title = kwargs.get('title')

    # 打开新标签页并切换到新标签页
    driver.switch_to.new_window('tab')

    # 浏览器实例现在可以被重用，进行你的自动化操作
    driver.get(xiaohongshu_site)
    time.sleep(3)  # 等待页面加载

    # 设置等待
    wait = WebDriverWait(driver, 15)

    # 检查视频是否已上传（通过检查页面是否有预览视频）
    video_preview = None
    try:
        video_preview = driver.find_element(By.CSS_SELECTOR, '.preview-new .name')
        print(f"检测到视频已上传: {video_preview.text}")
    except:
        pass

    if not video_preview:
        print("开始上传视频...")
        try:
            file_input = driver.find_element(By.CLASS_NAME, 'upload-input')
            file_input.send_keys(video_file)
            time.sleep(15)  # 等待视频上传
            # 等待视频预览出现
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.preview-new .name')))
            print("视频上传完成")
        except Exception as e:
            print(f"视频上传失败: {e}")
    else:
        print("视频已存在，等待页面稳定...")
        time.sleep(3)

    time.sleep(2)

    # 设置标题
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.d-text')))
        time.sleep(1)
        
        title_input = driver.find_element(By.CSS_SELECTOR, '.d-text')
        title_text = title if title else ""
        use_common = st.session_state.get('video_publish_use_common_config')
        if use_common:
            common_title = st.session_state.get('video_publish_title_prefix')
        else:
            common_title = st.session_state.get('video_publish_xiaohongshu_title_prefix')
        
        # 标题中可能包含 #话题，需要移除话题部分
        pure_title = title_text.split('#')[0].strip() if '#' in title_text else title_text
        
        # 先清空标题
        title_input.clear()
        time.sleep(0.5)
        
        # 标题有20字长度限制（不使用前缀）
        if len(pure_title) <= 20:
            title_input.send_keys(pure_title)
        else:
            title_input.send_keys(pure_title[:20])
        print(f"标题设置完成: {pure_title}")
        time.sleep(2)
    except Exception as e:
        print(f"标题设置失败: {e}")

    # 设置内容 - 使用模拟键盘输入方式
    try:
        # 先滚动到编辑区域上方
        driver.execute_script("window.scrollTo(0, 400);")
        time.sleep(1)

        # 读取内容
        if text_file:
            content_text = read_file_start_with_secondline(text_file)
        else:
            content_text = ""
        use_common = st.session_state.get('video_publish_use_common_config')
        if use_common:
            tags = st.session_state.get('video_publish_tags')
        else:
            tags = st.session_state.get('video_publish_xiaohongshu_tags')
        tags = tags.split()

        # 获取话题标签（去掉#号）
        tag_texts = [tag.replace('#', '').strip() for tag in tags]

        print(f"开始设置正文内容，长度: {len(content_text)}")

        # 找到编辑器并点击激活
        editor = driver.find_element(By.CSS_SELECTOR, '.tiptap.ProseMirror')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor)
        time.sleep(1)
        
        # 点击编辑器激活
        driver.execute_script("arguments[0].click();", editor)
        time.sleep(1)

        # 使用 ActionChains 模拟键盘输入
        import pyperclip
        import sys
        from selenium.webdriver import Keys
        
        # 先复制内容到剪贴板
        pyperclip.copy(content_text)
        
        # Ctrl+V 粘贴
        cmd_ctrl = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
        action_chains = webdriver.ActionChains(driver)
        action_chains.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl)
        action_chains.perform()
        time.sleep(2)

        # 输入话题标签
        for tag in tag_texts:
            # 按回车换行
            action_chains.send_keys(Keys.RETURN)
            action_chains.perform()
            time.sleep(0.5)
            
            # 输入话题（带#号）
            pyperclip.copy(f'#{tag}')
            action_chains.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl)
            action_chains.perform()
            time.sleep(0.5)

        print("正文内容设置完成")
    except Exception as e:
        print(f"正文内容设置失败: {e}")
        import traceback
        traceback.print_exc()

    # 发布 - 通过 shadow DOM
    auto_publish = st.session_state.get('video_publish_auto_publish')
    if auto_publish:
        print("开始自动发布...")
        time.sleep(2)
        
        # 先滚动到页面底部，确保发布按钮可见
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        # 尝试点击发布按钮
        driver.execute_script("""
            var btn = document.querySelector('xhs-publish-btn');
            if (btn && btn.shadowRoot) {
                var publishBtn = btn.shadowRoot.querySelector('.bg-red');
                if (publishBtn) {
                    publishBtn.click();
                    console.log('发布按钮已点击');
                } else {
                    console.log('未找到发布按钮 .bg-red');
                    // 打印 shadowRoot 内容
                    console.log('Shadow root children:', btn.shadowRoot.innerHTML);
                }
            } else {
                console.log('未找到 xhs-publish-btn');
            }
        """)
        print("发布操作已完成，请检查浏览器")







