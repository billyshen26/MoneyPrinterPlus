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

import sys

import pyperclip
from selenium import webdriver
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
import streamlit as st
import time
from config.config import bilibili_site
from tools.file_utils import read_head, read_file_with_extra_enter, read_file_start_with_secondline


def bilibili_publisher(driver, video_file, text_file, **kwargs):
    title = kwargs.get('title')

    # 打开新标签页并切换到新标签页
    driver.switch_to.new_window('tab')

    # 浏览器实例现在可以被重用，进行你的自动化操作
    driver.get(bilibili_site)
    time.sleep(3)  # 等待页面加载

    # 设置等待
    wait = WebDriverWait(driver, 15)

    # 上传视频 - 使用正确的新版选择器
    print("开始上传视频到 Bilibili...")
    try:
        # 新版 B 站使用隐藏的 input[type="file"] 上传
        upload_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"][accept*="mp4"]')
        print("找到文件上传输入框")
        upload_input.send_keys(video_file)
        print("视频上传中，请等待...")
        time.sleep(15)  # 等待视频上传
        print("视频上传完成")
    except Exception as e:
        print(f"视频上传失败: {e}")
        try:
            # 备选：直接找所有文件输入框
            upload_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
            if upload_inputs:
                print(f"找到 {len(upload_inputs)} 个文件上传框，尝试第一个")
                upload_inputs[0].send_keys(video_file)
                print("视频上传中...")
                time.sleep(15)
        except Exception as e2:
            print(f"备选上传也失败: {e2}")
            return

    # 等待表单加载
    time.sleep(5)

    # 设置标题
    try:
        print("等待并设置标题...")
        time.sleep(3)  # 等待表单加载
        
        # 新版 B 站标题输入框选择器
        title_selectors = [
            'input[placeholder*="标题"]',
            'input[placeholder*="选"]',
            '.title-input input',
            'input.bili-input',
            'input[class*="title"]'
        ]
        
        title_input = None
        for selector in title_selectors:
            try:
                title_input = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"找到标题输入框: {selector}")
                break
            except:
                continue
        
        if title_input:
            # 使用传入的标题
            title_text = title if title else ""
            print(f"[DEBUG] ========== 标题设置开始 ==========")
            print(f"[DEBUG] 原始标题长度: {len(title_text)}")
            print(f"[DEBUG] 原始标题repr: {repr(title_text)}")
            print(f"[DEBUG] 原始标题中#数量: {title_text.count('#')}")
            print(f"[DEBUG] 原始标题: [{title_text}]")

            # 统计标题中的话题数量（保存原始话题数量）
            original_topic_count = title_text.count('#')
            print(f"[DEBUG] 话题数量: {original_topic_count}")

            # 标题中可能包含 #话题，需要移除话题部分，只保留纯标题
            pure_title = title_text.split('#')[0].strip() if '#' in title_text else title_text
            print(f"[DEBUG] 纯标题: [{pure_title}]")

            # 清空并输入（不使用前缀）
            title_input.clear()
            time.sleep(0.5)
            
            # 标题有80字长度限制（不使用前缀）
            print(f"[DEBUG] 最终标题长度: {len(pure_title)}")
            if len(pure_title) <= 80:
                title_input.send_keys(pure_title)
            else:
                title_input.send_keys(pure_title[:80])
            print(f"标题设置完成: [{pure_title}]")
            print(f"[DEBUG] ========== 标题设置结束 ==========")
            time.sleep(2)
        else:
            print("未找到标题输入框")
    except Exception as e:
        print(f"标题设置失败: {e}")
        import traceback
        traceback.print_exc()

    # 设置标签
    try:
        print("开始设置标签...")
        tags_selectors = [
            'input[placeholder*="标签"]',
            'input[placeholder*="Enter"]',
            'input[placeholder*="回车"]',
            '.tag-input input'
        ]
        
        tags_input = None
        for selector in tags_selectors:
            try:
                tags_input = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"找到标签输入框: {selector}")
                break
            except:
                continue
        
        if tags_input:
            # 清空现有标签
            for _ in range(15):
                tags_input.send_keys(Keys.BACKSPACE)
                time.sleep(0.2)
            
            use_common = st.session_state.get('video_publish_use_common_config')
            if use_common:
                tags = st.session_state.get('video_publish_tags')
            else:
                tags = st.session_state.get('video_publish_bilibili_tags')
            tags = tags.split()
            print(f"[DEBUG] 配置的标签列表: {tags}")
            print(f"[DEBUG] 配置的标签数量: {len(tags)}")
            
            # 统计标题中的话题数量（标题中如果有话题会被B站自动识别）
            title_tags_count = len(title_text.split('#')) - 1 if '#' in title_text else 0
            print(f"[DEBUG] 标题中的话题数量: {title_tags_count}")
            # B站最多4个标签，减去标题中已占用的
            max_config_tags = max(0, 4 - title_tags_count)
            print(f"[DEBUG] 最大可添加配置标签数: {max_config_tags}")
            
            cmd_ctrl = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
            i = 0
            for tag in tags:
                if i >= max_config_tags:  # 最多添加剩余可用标签数量
                    print(f"[DEBUG] 已达标签上限 {max_config_tags}，停止添加")
                    break
                tag_clean = tag.strip()
                if tag_clean:
                    print(f"[DEBUG] 添加标签 {i+1}: {tag_clean}")
                    tags_input.send_keys(' ')
                    pyperclip.copy(tag_clean)
                    action = ActionChains(driver)
                    action.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl)
                    action.perform()
                    time.sleep(0.5)
                    tags_input.send_keys(Keys.ENTER)
                    time.sleep(0.5)
                    i += 1
            print(f"[DEBUG] 标签设置完成: 共添加 {i} 个")
        else:
            print("未找到标签输入框")
    except Exception as e:
        print(f"标签设置失败: {e}")

    # 设置简介/内容
    try:
        print("开始设置简介...")
        content_selectors = [
            'textarea[placeholder*="简介"]',
            'textarea[placeholder*="描述"]',
            'textarea.bili-textarea',
            '[contenteditable="true"]'
        ]
        
        content = None
        for selector in content_selectors:
            try:
                content = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"找到内容输入框: {selector}")
                break
            except:
                continue
        
        if content:
            if text_file:
                content_text = read_file_start_with_secondline(text_file)
            else:
                content_text = ""
            if content_text:
                pyperclip.copy(content_text)
            
            # 点击激活
            driver.execute_script("arguments[0].click();", content)
            time.sleep(0.5)
            
            cmd_ctrl = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
            action = ActionChains(driver)
            action.key_down(cmd_ctrl).send_keys('a').key_up(cmd_ctrl)  # 全选
            action.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl)  # 粘贴
            action.perform()
            print("简介设置完成")
            time.sleep(2)
        else:
            print("未找到简介输入框")
    except Exception as e:
        print(f"简介设置失败: {e}")

    # 发布
    auto_publish = st.session_state.get('video_publish_auto_publish')
    if auto_publish:
        print("开始自动发布...")
        time.sleep(2)
        try:
            # 尝试多种发布按钮选择器
            publish_selectors = [
                '.submit-add',
                '.bili-publish',
                'button[class*="submit"]',
                'button:contains("发布")'
            ]
            
            for selector in publish_selectors:
                try:
                    publish_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    driver.execute_script("arguments[0].click();", publish_btn)
                    print(f"发布按钮点击成功")
                    break
                except:
                    continue
            else:
                print("未找到发布按钮")
        except Exception as e:
            print(f"发布失败: {e}")
        print("请检查 Bilibili 页面确认发布状态")


