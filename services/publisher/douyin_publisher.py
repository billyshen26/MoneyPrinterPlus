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

import os
import sys
import traceback

import pyperclip
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
import streamlit as st

import time

from config.config import douyin_site
from tools.file_utils import read_head, read_file_with_extra_enter, read_file_start_with_secondline


def _read_usernames(usernames_file):
    """读取用户名列表"""
    if not usernames_file or not os.path.exists(usernames_file):
        return []
    try:
        with open(usernames_file, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception:
        return []


def _format_comment(template, usernames):
    """把模板中的 {} 依次替换为用户名"""
    if not usernames:
        return None
    return template.format(*usernames)


def douyin_publisher(driver, video_file, text_file, usernames_file=None):

    # driver.switch_to.window(driver.window_handles[0])

    # 打开新标签页并切common_config换到新标签页
    driver.switch_to.new_window('tab')

    # 浏览器实例现在可以被重用，进行你的自动化操作
    driver.get(douyin_site)
    time.sleep(2)  # 等待2秒

    # 设置等待
    wait = WebDriverWait(driver, 10)

    # 上传视频按钮
    # file_input = driver.find_element(By.NAME,'upload-btn')
    file_input = driver.find_element(By.XPATH, '//input[@type="file"]')
    file_input.send_keys(video_file)
    time.sleep(10)  # 等待
    # 等待视频上传完毕
    # wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'semi-input semi-input-default')))

    # 设置标题
    title = driver.find_element(By.XPATH, '//input[@class="semi-input semi-input-default"]')
    title_text = read_head(text_file)
    use_common = st.session_state.get('video_publish_use_common_config')
    if use_common:
        common_title = st.session_state.get('video_publish_title_prefix')
    else:
        common_title = st.session_state.get('video_publish_douyin_title_prefix')

    # 标题有30字长度限制
    if len(common_title + title_text) <= 30:
        title.send_keys(common_title + title_text)
    else:
        title.send_keys(title_text)
    time.sleep(2)

    # 设置内容
    content = driver.find_element(By.XPATH, '//div[@data-placeholder="添加作品简介"]')
    content.click()
    time.sleep(2)
    cmd_ctrl = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
    # 将要粘贴的文本内容复制到剪贴板
    content_text = read_file_start_with_secondline(text_file)
    pyperclip.copy(content_text)
    action_chains = webdriver.ActionChains(driver)
    # 模拟实际的粘贴操作
    action_chains.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
    time.sleep(2)

    # 设置tags
    if use_common:
        tags = st.session_state.get('video_publish_tags')
    else:
        tags = st.session_state.get('video_publish_douyin_tags')
    tags = tags.split()
    for tag in tags:
        is_firefox = st.session_state.get("video_publish_driver_type") == 'firefox'
        # firefox没有原创按钮？
        if not is_firefox:
            print("tag:", tag)
            content.send_keys(' ')
            content.send_keys(tag)
            time.sleep(2)
            content.send_keys(Keys.ENTER)
            time.sleep(1)
            content.send_keys(' ')
            time.sleep(2)
        else:
            print("firefox tag:", tag)
            content.send_keys(' ')
            pyperclip.copy(tag)
            action_chains.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
            time.sleep(2)
            content.send_keys(' ')
            time.sleep(1)

    # 设置合集
    if use_common:
        collection = st.session_state.get('video_publish_collection_name')
    else:
        collection = st.session_state.get('video_publish_douyin_collection_name')
    if collection:
        collection_tag = driver.find_element(By.XPATH, '//div[contains(text(),"选择合集")]')
        collection_tag.click()
        time.sleep(1)
        collection_to_select = driver.find_element(By.XPATH, f'//div[@class="semi-select-option collection-option"]//span[text()="{collection}"]')
        collection_to_select.click()
        time.sleep(1)

    # 设置是否允许他人保存视频
    try:
        save_switch = driver.find_element(By.CSS_SELECTOR, 'input.dy-creator-content-switch-native-control')
        is_checked = save_switch.get_attribute('aria-checked')
        if is_checked == 'false':
            save_switch.click()
        time.sleep(1)
    except Exception:
        try:
            save_switch = driver.find_element(By.XPATH, '//input[@role="switch" and contains(@class, "dy-creator-content-switch")]')
            save_switch.click()
            time.sleep(1)
        except Exception:
            pass
    # 发布
    publish_button = driver.find_element(By.CSS_SELECTOR, 'button.button-dhlUZE.primary-cECiOJ')
    auto_publish = st.session_state.get('video_publish_auto_publish')
    auto_comment = st.session_state.get('video_publish_douyin_auto_comment')
    if auto_publish:
        print("auto publish")
        publish_button.click()
        time.sleep(3)

        if auto_comment and usernames_file:
            try:
                comment_template = st.session_state.get('video_publish_douyin_comment_template', '这也太有才了 @{} @{} @{} @{}，你也来看看！')
                usernames = _read_usernames(usernames_file)
                if usernames:
                    comment_text = _format_comment(comment_template, usernames)
                    if comment_text:
                        time.sleep(5)
                        current_url = driver.current_url
                        print(f"当前页面: {current_url}")
                        # 直接在发布页面评论
                        _post_douyin_comment(driver, comment_text)
            except Exception as e:
                print(f"自动评论失败: {e}")
                traceback.print_exc()


def _post_douyin_comment(driver, comment_text):
    """在抖音视频页面发布评论"""
    try:
        time.sleep(3)
        # 尝试点击评论区域
        comment_area = driver.find_element(By.XPATH, '//div[@placeholder="发友善评论~"]')
        comment_area.click()
        time.sleep(2)
        pyperclip.copy(comment_text)
        cmd_ctrl = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
        action_chains = webdriver.ActionChains(driver)
        action_chains.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
        time.sleep(2)
        # 发送评论
        send_btn = driver.find_element(By.XPATH, '//button[contains(@class, "comment-send")]')
        send_btn.click()
        time.sleep(2)
        print(f"评论已发送: {comment_text}")
    except Exception as e:
        print(f"评论发送失败: {e}")
        traceback.print_exc()







