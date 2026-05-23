#  Copyright © [2024] 程序那些事
#
#  All rights reserved. This software and associated documentation files (the "Software") are provided for personal and educational use only. Commercial use of the Software is strictly prohibited unless explicit permission is obtained from the author.
#
#  Permission is hereby granted to any person to use, copy, and modify the Software for non-commercial purposes, provided that the following conditions are met:
#
#  1. The original copyright notice and this permission notice must be included in all copies or substantial portions of the Software.
#  2. Modifications, if any, represent the original copyright information and must not imply that the modified version is an official version of the Software.
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
import streamlit as st

from config.config import app_title, load_session_state_from_yaml, save_session_state_to_yaml
from pages.common import common_ui
from services.video.grid_service import get_video_files_from_folder, extract_audio_from_video, VideoGridService

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

default_bg_music_dir = os.path.join(script_dir, "../bgmusic")
default_bg_music_dir = os.path.abspath(default_bg_music_dir)

load_session_state_from_yaml('05_first_visit')


def _reset_grid_selection():
    """重置视频选择状态（切换文件夹时调用）"""
    from services.video.grid_service import reset_video_selection
    reset_video_selection()


def _reset_selection():
    from services.video.grid_service import reset_video_selection
    reset_video_selection()
    st.rerun()

def generate_grid_video(video_generator):
    save_session_state_to_yaml()

    video_folder = st.session_state.get("video_grid_folder")
    if not video_folder or not os.path.exists(video_folder):
        st.error("请输入有效的视频文件夹路径")
        return

    video_files = get_video_files_from_folder(video_folder)
    if len(video_files) < 4:
        st.error(f"视频文件夹中需要至少4个视频文件，当前只有 {len(video_files)} 个")
        return

    layout = st.session_state.get("video_grid_layout", "4grid")
    bg_music_video = st.session_state.get("background_music_video", None)
    bgm_volume = st.session_state.get("video_grid_bgm_volume", 0.3)

    background_music = None
    if bg_music_video and os.path.exists(bg_music_video):
        background_music = extract_audio_from_video(bg_music_video)

    with video_generator:
        st_area = st.status("正在生成视频组合...", expanded=True)
        with st_area:
            st.write("初始化视频组合服务...")
            grid_service = VideoGridService(
                video_list=video_files,
                layout=layout,
                background_music=background_music,
                bgm_volume=bgm_volume,
                video_folder=video_folder
            )

            st.write("正在生成宫格视频...")
            result_video = grid_service.generate_grid_video()

            if result_video and os.path.exists(result_video):
                st.session_state["grid_result_video"] = result_video
                st_area.update(label="视频组合生成完成!", state="complete", expanded=False)
            else:
                st_area.update(label="视频组合生成失败!", state="error", expanded=False)


common_ui()

st.markdown(f"<h1 style='text-align: center; font-weight:bold; font-family:comic sans ms; padding-top: 0rem;'> \
            {app_title}</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center;padding-top: 0rem;'>视频组合工具</h2>", unsafe_allow_html=True)

folder_container = st.container(border=True)
with folder_container:
    st.subheader("视频来源")
    video_folder = st.text_input(
        label="视频文件夹路径",
        placeholder="请输入视频文件夹路径",
        key="video_grid_folder",
        on_change=_reset_grid_selection
    )

    col_reset, _ = st.columns([1, 5])
    with col_reset:
        st.button("重置选择", on_click=_reset_selection, help="重置已选视频记录，重新开始随机选择")

    if video_folder and os.path.exists(video_folder):
        video_files = get_video_files_from_folder(video_folder)
        st.info(f"找到 {len(video_files)} 个视频文件")

        if len(video_files) >= 4:
            st.success("视频数量足够，可以生成4宫格或9宫格视频")
        else:
            st.warning("视频数量不足，至少需要4个视频文件")

config_container = st.container(border=True)
with config_container:
    st.subheader("视频组合配置")

    col1, col2 = st.columns(2)
    with col1:
        layout_options = {"4grid": "4宫格 (2x2)", "9grid": "9宫格 (3x3)"}
        st.selectbox(
            label="宫格布局",
            key="video_grid_layout",
            options=layout_options,
            format_func=lambda x: layout_options[x],
            help="4宫格需要至少4个视频，9宫格需要至少9个视频"
        )

    with col2:
        st.selectbox(
            label="视频帧率",
            key="video_fps",
            options=[20, 25, 30],
            help="输出视频的帧率"
        )

    st.markdown("---")
    st.subheader("背景音乐设置")

    bgm_col1, bgm_col2 = st.columns([2, 1])
    with bgm_col1:
        folder_video_files = get_video_files_from_folder(video_folder) if video_folder and os.path.exists(video_folder) else []
        if len(folder_video_files) > 0:
            video_options = {v: os.path.basename(v) for v in folder_video_files}
            st.selectbox(
                label="选择背景音乐来源（从视频中提取）",
                key="background_music_video",
                options=video_options,
                format_func=lambda x: video_options.get(x, x),
                help="选择其中一个视频的音频作为背景音乐"
            )
        else:
            st.selectbox(
                label="选择背景音乐来源",
                key="background_music_video",
                options=[""],
                disabled=True
            )

    with bgm_col2:
        st.slider(
            label="背景音乐音量",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.1,
            key="video_grid_bgm_volume",
            help="背景音乐的音量 (0.0-1.0)"
        )

preview_container = st.container(border=True)
with preview_container:
    st.subheader("视频预览")

    if video_folder and os.path.exists(video_folder):
        folder_video_files = get_video_files_from_folder(video_folder)
        layout = st.session_state.get("video_grid_layout", "4grid")
        required = 4 if layout == "4grid" else 9

        cols = st.columns(min(len(folder_video_files[:required]), 4))
        for idx, video_file in enumerate(folder_video_files[:required]):
            with cols[idx % 4]:
                st.video(video_file)
                st.caption(f"视频 {idx + 1}: {os.path.basename(video_file)}")
    else:
        st.info("请先输入视频文件夹路径")

video_generator = st.container(border=True)
with video_generator:
    st.button(
        label="生成视频组合",
        type="primary",
        on_click=generate_grid_video,
        args=(video_generator,)
    )

result_video = st.session_state.get("grid_result_video")
if result_video and os.path.exists(result_video):
    st.markdown("---")
    st.subheader("生成结果")
    st.video(result_video)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="下载视频",
            data=open(result_video, 'rb'),
            file_name=os.path.basename(result_video),
            mime="video/mp4"
        )
