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

import streamlit as st

from config.config import transition_types, fade_list, load_session_state_from_yaml, \
    save_session_state_to_yaml, app_title
from main import main_generate_simple_merge
from pages.common import common_ui
from tools.utils import get_file_map_from_dir

# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)

default_bg_music_dir = os.path.join(script_dir, "../bgmusic")
default_bg_music_dir = os.path.abspath(default_bg_music_dir)

load_session_state_from_yaml('04_first_visit')


def generate_simple_merge(video_generator):
    save_session_state_to_yaml()
    main_generate_simple_merge(video_generator)


common_ui()

st.markdown(f"<h1 style='text-align: center; font-weight:bold; font-family:comic sans ms; padding-top: 0rem;'> \
            {app_title}</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center;padding-top: 0rem;'>多视频合并工具</h2>", unsafe_allow_html=True)

# 文件夹选择
folder_container = st.container(border=True)
with folder_container:
    st.subheader("视频来源")
    st.text_input(
        label="视频文件夹路径",
        placeholder="请输入视频文件夹路径",
        key="simple_merge_video_folder"
    )

# 背景音乐
bg_music_container = st.container(border=True)
with bg_music_container:
    st.subheader("背景音乐")
    llm_columns = st.columns(2)
    with llm_columns[0]:
        st.text_input(
            label="背景音乐目录",
            placeholder="输入背景音乐目录",
            value=default_bg_music_dir,
            key="background_music_dir"
        )

    with llm_columns[1]:
        nest_columns = st.columns(3)
        with nest_columns[0]:
            st.checkbox(label="启用背景音乐", key="enable_background_music", value=True)
        with nest_columns[1]:
            bg_music_list = get_file_map_from_dir(st.session_state.get("background_music_dir", default_bg_music_dir), ".mp3,.wav")
            st.selectbox(
                label="背景音乐",
                key="background_music",
                options=bg_music_list,
                format_func=lambda x: bg_music_list.get(x, x)
            )
        with nest_columns[2]:
            st.slider(label="背景音乐音量", min_value=0.0, value=0.3, max_value=1.0, step=0.1,
                      key="background_music_volume")

# 视频配置
video_container = st.container(border=True)
with video_container:
    st.subheader("视频配置")
    llm_columns = st.columns(3)
    with llm_columns[0]:
        layout_options = {"portrait": "竖屏", "landscape": "横屏", "square": "方形"}
        st.selectbox(
            label="视频布局",
            key="video_layout",
            options=layout_options,
            format_func=lambda x: layout_options[x]
        )
    with llm_columns[1]:
        st.selectbox(label="视频帧率", key="video_fps", options=[20, 25, 30])
    with llm_columns[2]:
        if st.session_state.get("video_layout") == "portrait":
            video_size_options = {"1080x1920": "1080p", "720x1280": "720p", "480x960": "480p", "360x720": "360p",
                                  "240x480": "240p"}
        elif st.session_state.get("video_layout") == "landscape":
            video_size_options = {"1920x1080": "1080p", "1280x720": "720p", "960x480": "480p", "720x360": "360p",
                                  "480x240": "240p"}
        else:
            video_size_options = {"1080x1080": "1080p", "720x720": "720p", "480x480": "480p", "360x360": "360p",
                                  "240x240": "240p"}
        st.selectbox(
            label="视频尺寸",
            key="video_size",
            options=video_size_options,
            format_func=lambda x: video_size_options[x]
        )

    llm_columns = st.columns(4)
    with llm_columns[0]:
        st.checkbox(label="启用转场特效", key="enable_video_transition_effect", value=True)
    with llm_columns[1]:
        st.selectbox(label="转场类型", key="video_transition_effect_type", options=transition_types)
    with llm_columns[2]:
        st.selectbox(label="转场效果", key="video_transition_effect_value", options=fade_list)
    with llm_columns[3]:
        st.selectbox(label="转场时长", key="video_transition_effect_duration",
                     options=["1", "2"])

# 字幕
subtitle_container = st.container(border=True)
with subtitle_container:
    st.subheader("字幕设置")
    llm_columns = st.columns(4)
    with llm_columns[0]:
        st.checkbox(label="启用字幕", key="enable_subtitles", value=True)
    with llm_columns[1]:
        st.selectbox(
            label="字幕字体",
            key="subtitle_font",
            options=[
                "Songti SC Bold",
                "Songti SC Black",
                "Songti SC Light",
                "STSong",
                "Songti SC Regular",
                "PingFang SC Regular",
                "PingFang SC Medium",
                "PingFang SC Semibold",
                "PingFang SC Light",
                "PingFang SC Thin",
                "PingFang SC Ultralight"
            ]
        )
    with llm_columns[2]:
        st.selectbox(label="字幕大小", key="subtitle_font_size", index=1,
                     options=[4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24])
    with llm_columns[3]:
        st.selectbox(label="字幕行数", key="captioning_lines", index=1,
                     options=[1, 2])

    llm_columns = st.columns(4)
    with llm_columns[0]:
        subtitle_position_options = {
            5: "顶部左侧",
            6: "顶部居中",
            7: "顶部右侧",
            9: "中间左侧",
            10: "居中",
            11: "中间右侧",
            1: "底部左侧",
            2: "底部居中",
            3: "底部右侧"
        }
        st.selectbox(
            label="字幕位置",
            key="subtitle_position",
            index=7,
            options=subtitle_position_options,
            format_func=lambda x: subtitle_position_options[x]
        )
    with llm_columns[1]:
        st.color_picker(label="字幕颜色", key="subtitle_color", value="#FFFFFF")
    with llm_columns[2]:
        st.color_picker(label="字幕描边颜色", key="subtitle_border_color", value="#000000")
    with llm_columns[3]:
        st.slider(label="字幕描边宽度", min_value=0.0, value=0.0, max_value=4.0, step=1.0,
                  key="subtitle_border_width")

# 原创性提升配置
originality_container = st.container(border=True)
with originality_container:
    st.subheader("原创性提升")
    llm_columns = st.columns(2)
    with llm_columns[0]:
        st.checkbox(label="启用原创性提升", key="enable_video_originality", value=True,
                   help="开启后将对视频进行随机起点截取、滤镜处理和水印添加")
    with llm_columns[1]:
        filter_options = {"none": "无", "light": "轻微", "medium": "中等", "strong": "明显"}
        st.selectbox(
            label="滤镜强度",
            key="video_filter_preset",
            options=filter_options,
            format_func=lambda x: filter_options[x],
            help="滤镜会微调视频的色彩饱和度、对比度等"
        )

    llm_columns = st.columns(3)
    with llm_columns[0]:
        st.slider(label="随机起点最大偏移（秒）", min_value=0.0, max_value=3.0,
                  value=2.0, step=0.5, key="video_random_start_max_offset",
                  help="随机从视频的0-X秒位置开始截取")
    with llm_columns[1]:
        st.slider(label="最大截取时长（秒）", min_value=3.0, max_value=10.0,
                  value=5.0, step=0.5, key="video_random_start_max_duration",
                  help="每个视频片段最多截取多少秒")

    with llm_columns[2]:
        st.text_input(
            label="水印图片路径",
            key="video_watermark_path",
            placeholder="输入水印图片路径",
            help="水印图片的完整路径，支持 PNG/JPG"
        )
    with llm_columns[2]:
        watermark_pos_options = {
            "top_left": "左上角",
            "top_right": "右上角",
            "bottom_left": "左下角",
            "bottom_right": "右下角",
            "center": "居中"
        }
        st.selectbox(
            label="水印位置",
            key="video_watermark_position",
            options=watermark_pos_options,
            format_func=lambda x: watermark_pos_options[x]
        )

    llm_columns = st.columns(3)
    with llm_columns[0]:
        st.slider(label="水印透明度", min_value=0.1, max_value=1.0,
                  value=0.7, step=0.1, key="video_watermark_opacity")
    with llm_columns[1]:
        st.slider(label="水印大小比例", min_value=0.05, max_value=0.30,
                  value=0.15, step=0.05, key="video_watermark_scale",
                  help="水印相对于视频宽度的比例")

# 生成视频
video_generator = st.container(border=True)
with video_generator:
    st.button(label="生成视频", type="primary", on_click=generate_simple_merge,
              args=(video_generator,))

result_video_file = st.session_state.get("result_video_file")
if result_video_file and os.path.exists(result_video_file):
    st.video(result_video_file)
