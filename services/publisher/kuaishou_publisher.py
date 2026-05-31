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
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import streamlit as st

import time

from config.config import kuaishou_site
from tools.file_utils import read_file_with_extra_enter


def kuaishou_publisher(driver, video_file, text_file, **kwargs):
    title = kwargs.get('title')

    print(f"[DEBUG] ========== 快手发布开始 ==========")
    print(f"[DEBUG] 传入的标题: [{title}]")
    print(f"[DEBUG] 标题中#数量: {title.count('#') if title else 0}")

    # driver.switch_to.window(driver.window_handles[0])

    # 打开新标签页并切换到新标签页
    driver.switch_to.new_window('tab')

    # 浏览器实例现在可以被重用，进行你的自动化操作
    driver.get(kuaishou_site)
    time.sleep(2)  # 等待2秒

    # 设置等待
    wait = WebDriverWait(driver, 10)

    # 上传视频按钮
    file_input = driver.find_element(By.XPATH,'//input[@type="file"]')
    file_input.send_keys(video_file)
    time.sleep(10)  # 等待
    # 等待视频上传完毕 - 快手新页面使用 id="work-description-edit"
    wait.until(EC.presence_of_element_located((By.XPATH, '//div[@id="work-description-edit"]')))

    # 设置标题（快手没有单独的标题输入框，标题包含在内容中）
    use_common = st.session_state.get('video_publish_use_common_config')
    if use_common:
        common_title = st.session_state.get('video_publish_title_prefix')
    else:
        common_title = st.session_state.get('video_publish_kuaishou_title_prefix')

    # 设置内容 - 使用新的 id 定位
    content = driver.find_element(By.XPATH, '//div[@id="work-description-edit"]')
    content.click()
    time.sleep(2)
    cmd_ctrl = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL
    
    # 使用完整的标题（包括话题）
    full_title = title if title else ""
    print(f"[DEBUG] 输入的标题: [{full_title}]")
    
    # 如果有文本文件，读取内容；否则只使用标题
    if text_file:
        content_text = read_file_with_extra_enter(text_file)
        content_text = content_text[:450]
        full_text = full_title + '\n\n' + content_text
    else:
        full_text = full_title
    
    print(f"[DEBUG] 粘贴内容中#数量: {full_text.count('#')}")
    pyperclip.copy(full_text)
    action_chains = webdriver.ActionChains(driver)
    action_chains.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
    time.sleep(2)
    
    # 点击"智能话题"按钮，让快手推荐话题
    try:
        print(f"[DEBUG] 点击智能话题按钮...")
        # 先滚动到合适位置
        driver.execute_script("window.scrollTo(0, 200);")
        time.sleep(1)
        
        ai_topic_button = driver.find_element(By.XPATH, '//div[contains(@class, "_ai-button-icon-topic")]')
        # 使用 JavaScript 点击避免被遮挡
        driver.execute_script("arguments[0].click();", ai_topic_button)
        time.sleep(3)  # 等待推荐话题出现
        
        # 查找推荐的话题元素
        topic_items = driver.find_elements(By.CSS_SELECTOR, 'div._ai-topics-item_1gvw3_170')
        print(f"[DEBUG] 找到 {len(topic_items)} 个推荐话题")
        
        # 选中前4个推荐话题
        i = 0
        for topic_item in topic_items[:4]:
            try:
                # 使用 JavaScript 点击
                driver.execute_script("arguments[0].click();", topic_item)
                time.sleep(0.5)
                i += 1
                print(f"[DEBUG] 已选中话题 {i}")
            except Exception as e:
                print(f"[DEBUG] 选中话题 {i+1} 失败: {e}")
        
        print(f"[DEBUG] 成功选中 {i} 个推荐话题")
    except Exception as e:
        print(f"[DEBUG] 智能话题点击失败: {e}")

    # 跳过手动设置标签（改用智能话题推荐）
    # if use_common:
    #     tags = st.session_state.get('video_publish_tags')
    # else:
    #     tags = st.session_state.get('video_publish_kuaishou_tags')
    # tags = tags.split()
    # print(f"[DEBUG] 配置的标签: {tags}")
    
    # i =0
    # for tag in tags:
    #     # 快手只接受三个标签
    #     if i == 3:
    #         break
    #     print(f"[DEBUG] 添加标签 {i+1}: [{tag}]")
    #     content.send_keys(' ')
    #     content.send_keys(tag)
    #     time.sleep(2)
    #     content.send_keys(Keys.ENTER)
    #     time.sleep(1)
    #     content.send_keys(' ')
    #     time.sleep(2)
    #     i=i+1
    # print(f"[DEBUG] 标签设置完成，共 {i} 个")
    print(f"[DEBUG] ========== 快手发布结束 ==========")

    # 设置合集（新版页面可能没有此功能）
    try:
        if use_common:
            collection = st.session_state.get('video_publish_collection_name')
        else:
            collection = st.session_state.get('video_publish_kuaishou_collection_name')
        if collection:
            collection_tag = driver.find_element(By.XPATH, '//span[contains(text(),"选择要加入到的合集")]')
            actions = ActionChains(driver)
            actions.move_to_element(collection_tag).click().perform()
            time.sleep(1)
            collection_to_select = driver.find_element(By.XPATH, f'//div[@label="{collection}"]')
            collection_to_select.click()
            time.sleep(1)
    except Exception:
        print("合集设置功能不可用或已在新版页面中移除")

    # 设置分区（新版页面可能没有此功能）
    try:
        domain = st.session_state.get('video_publish_enable_kuaishou_domain')
        if domain:
            print("设置领域")
            domain_tag = driver.find_element(By.XPATH, '//span[contains(text(),"请选择")]')
            actions = ActionChains(driver)
            actions.move_to_element(domain_tag).click().perform()
            time.sleep(1)
            domain_level1 = st.session_state.get('video_publish_kuaishou_domain_level1')
            domain_level_1 = driver.find_element(By.XPATH, f'//div[@title="{domain_level1}"]')
            actions = ActionChains(driver)
            actions.move_to_element(domain_level_1).click().perform()
            time.sleep(1)

            domain_level2 = st.session_state.get('video_publish_kuaishou_domain_level2')
            domain_level2_tag = driver.find_element(By.XPATH, '//span[contains(text(),"请选择")]')
            actions = ActionChains(driver)
            actions.move_to_element(domain_level2_tag).click().perform()
            time.sleep(1)

            domain_level_2 = driver.find_element(By.XPATH, f'//div[@title="{domain_level2}"]')
            actions = ActionChains(driver)
            actions.move_to_element(domain_level_2).click().perform()
            time.sleep(1)
    except Exception:
        print("分区设置功能不可用或已在新版页面中移除")
    
    # 设置是否允许他人保存视频（新版页面使用 checkbox）
    try:
        # 查找"允许下载此作品" checkbox 并取消勾选
        download_checkbox = driver.find_element(By.XPATH, '//input[@value="downloadType"]/ancestor::label')
        actions = ActionChains(driver)
        actions.move_to_element(download_checkbox).click().perform()
        time.sleep(1)
    except Exception:
        print("下载权限设置不可用")

    time.sleep(2)
    
    # 发布 - 定位底部按钮区域的"发布"按钮
    publish_buttons = driver.find_elements(By.XPATH, '//div[contains(@class,"_edit-section-btns_")]//div[text()="发布"]')
    if publish_buttons:
        publish_button = publish_buttons[0]
    else:
        # 备用方案：查找所有包含"发布"文本的按钮
        publish_button = driver.find_element(By.XPATH, '//div[contains(@class,"_button-primary_")]')
    auto_publish = st.session_state.get('video_publish_auto_publish')
    if auto_publish:
        print("auto publish")
        publish_button.click()







