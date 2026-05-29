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

import json
import os

import streamlit as st

from config.config import app_title, load_session_state_from_yaml, save_session_state_to_yaml, fade_list
from pages.common import common_ui
from services.video.sequential_merge_service import SequentialMergeService, get_video_files_from_folder
from tools.tr_utils import tr

load_session_state_from_yaml('08_first_visit')


def get_used_videos_file(video_folder):
    """获取视频文件夹对应的已使用记录文件路径"""
    return os.path.join(video_folder, ".used_videos.json")


def load_used_videos_from_file(video_folder):
    """从 JSON 文件加载已使用视频列表"""
    file_path = get_used_videos_file(video_folder)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("used_videos", [])
        except Exception as e:
            print(f"加载已使用视频记录失败: {e}")
    return []


def save_used_videos_to_file(video_folder, used_videos):
    """保存已使用视频列表到 JSON 文件"""
    file_path = get_used_videos_file(video_folder)
    try:
        import datetime
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"used_videos": used_videos, "last_updated": datetime.datetime.now().isoformat()}, f)
    except Exception as e:
        print(f"保存已使用视频记录失败: {e}")


def reset_used_videos_in_file(video_folder):
    """重置视频文件夹中的已使用记录"""
    file_path = get_used_videos_file(video_folder)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"删除已使用视频记录失败: {e}")


def generate_sequential_merge():
    main_generate_sequential_merge()


def main_generate_sequential_merge():
    video_folder = st.session_state.get("sequential_video_folder", "")
    video_count = st.session_state.get("sequential_video_count", 4)

    if not video_folder or not os.path.exists(video_folder):
        st.error(tr("Video folder does not exist"))
        return

    video_files = get_video_files_from_folder(video_folder)

    # 如果开启不重复使用视频，从文件加载并排除已使用的视频
    no_repeat = st.session_state.get("sequential_no_repeat", True)
    if no_repeat:
        used_videos = load_used_videos_from_file(video_folder)
        video_files = [v for v in video_files if v not in used_videos]

    if len(video_files) < video_count:
        st.error(tr("Not enough videos in folder. Need") + f" {video_count}, found {len(video_files)}")
        return

    selected_videos = video_files[:video_count]

    # 记录本次使用的视频到文件和 session_state
    if no_repeat:
        used_videos = load_used_videos_from_file(video_folder)
        used_videos.extend(selected_videos)
        save_used_videos_to_file(video_folder, used_videos)
        st.session_state["sequential_used_videos"] = used_videos

    with st.status(tr("Processing videos..."), expanded=True) as status:
        transition_type = st.session_state.get("sequential_transition_type", "xfade")
        transition_duration = st.session_state.get("sequential_transition_duration", 1.0)
        watermark_text = st.session_state.get("sequential_watermark_text", "")
        watermark_position = st.session_state.get("sequential_watermark_position", "bottom_right")
        cover_type = st.session_state.get("sequential_cover_type", "4grid")
        cover_timestamp = st.session_state.get("sequential_cover_timestamp", 2)

        service = SequentialMergeService(
            video_list=selected_videos,
            transition_type=transition_type,
            transition_duration=transition_duration,
            watermark_text=watermark_text if watermark_text else None,
            watermark_position=watermark_position,
            cover_type=cover_type,
            cover_timestamp=cover_timestamp,
            video_folder=video_folder,
            video_duration=st.session_state.get("sequential_video_duration", 10)
        )

        result = service.process_videos()

        if result and os.path.exists(result):
            st.session_state["sequential_result_video"] = result
            status.update(label=tr("Video generated successfully!"), state="complete", expanded=False)
            st.toast("视频生成成功！", icon="✅")
        else:
            status.update(label=tr("Video generation failed"), state="error")
            st.error("视频生成失败，请查看日志")


common_ui()

st.markdown(f"<h1 style='text-align: center; font-weight:bold; font-family:comic sans ms; padding-top: 0rem;'> \
            {app_title}</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center;padding-top: 0rem;'>顺序拼接视频工具</h2>", unsafe_allow_html=True)

# 视频来源配置
folder_container = st.container(border=True)
with folder_container:
    st.subheader("视频来源")

    video_folder = st.text_input(
        label="视频文件夹路径",
        placeholder="请输入视频文件夹路径",
        key="sequential_video_folder",
        help="选择包含视频文件的文件夹"
    )

    if video_folder and os.path.exists(video_folder):
        all_videos = get_video_files_from_folder(video_folder)
        st.info(f"文件夹中共有 {len(all_videos)} 个视频")
    else:
        all_videos = []

    llm_columns = st.columns([2, 1, 1])
    with llm_columns[0]:
        video_count = st.slider(
            label="选择视频数量",
            min_value=2,
            max_value=min(9, len(all_videos) if all_videos else 9),
            value=4,
            step=1,
            key="sequential_video_count",
            help="需要拼接的视频数量"
        )
    with llm_columns[1]:
        st.checkbox(
            label="不重复使用",
            key="sequential_no_repeat",
            value=True,
            help="已使用过的视频不再使用"
        )
    with llm_columns[2]:
        st.write("")  # 占位
        if st.button("刷新文件列表", use_container_width=True):
            st.session_state["refresh_trigger"] = not st.session_state.get("refresh_trigger", False)

    # 显示已使用视频数量（从文件加载）
    if st.session_state.get("sequential_no_repeat", True) and video_folder:
        used_videos = load_used_videos_from_file(video_folder)
        used_count = len(used_videos)
        available_count = max(0, len(all_videos) - used_count)

        if used_count > 0:
            st.info(f"已使用 {used_count} 个视频，当前可用 {available_count} 个")
            st.session_state["sequential_used_videos"] = used_videos

            # 确认重置对话框
            if "show_reset_confirm" not in st.session_state:
                st.session_state["show_reset_confirm"] = False

            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("重置已使用记录"):
                    st.session_state["show_reset_confirm"] = True

            if st.session_state["show_reset_confirm"]:
                st.warning("确定要重置已使用记录吗？这将允许已使用过的视频再次被使用。")
                confirm_col1, confirm_col2 = st.columns(2)
                with confirm_col1:
                    if st.button("确认重置", type="primary"):
                        reset_used_videos_in_file(video_folder)
                        st.session_state["sequential_used_videos"] = []
                        st.session_state["show_reset_confirm"] = False
                        st.rerun()
                with confirm_col2:
                    if st.button("取消"):
                        st.session_state["show_reset_confirm"] = False
                        st.rerun()

# 视频配置
video_container = st.container(border=True)
with video_container:
    st.subheader("视频配置")

    llm_columns = st.columns(4)
    with llm_columns[0]:
        video_layout = st.selectbox(
            label="视频布局",
            key="sequential_video_layout",
            options=["portrait", "landscape", "square"],
            format_func=lambda x: {"portrait": "竖屏", "landscape": "横屏", "square": "方形"}[x],
            help="视频的纵横比"
        )
    with llm_columns[1]:
        st.selectbox(
            label="视频帧率",
            key="sequential_video_fps",
            options=[25, 30],
            index=1,
            help="视频帧率（推荐30fps保证流畅）"
        )
    with llm_columns[2]:
        if video_layout == "portrait":
            video_size_options = {"1080x1920": "1080p", "720x1280": "720p"}
        elif video_layout == "landscape":
            video_size_options = {"1920x1080": "1080p", "1280x720": "720p"}
        else:
            video_size_options = {"1080x1080": "1080p", "720x720": "720p"}
        st.selectbox(
            label="视频尺寸",
            key="sequential_video_size",
            options=video_size_options,
            format_func=lambda x: video_size_options[x],
            help="输出视频的尺寸"
        )
    with llm_columns[3]:
        st.slider(
            label="视频时长（秒）",
            min_value=3,
            max_value=60,
            value=10,
            step=1,
            key="sequential_video_duration",
            help="每个视频截取的时长"
        )

# 转场与水印配置
transition_container = st.container(border=True)
with transition_container:
    st.subheader("转场与水印配置")

    llm_columns = st.columns(4)
    with llm_columns[0]:
        transition_type = st.selectbox(
            label="转场类型",
            key="sequential_transition_type",
            options=["none", "xfade"],
            format_func=lambda x: {"none": "无", "xfade": "交叉淡化"}[x],
            help="视频之间的转场效果"
        )
    with llm_columns[1]:
        st.slider(
            label="转场时长（秒）",
            min_value=0.5,
            max_value=3.0,
            value=1.0,
            step=0.5,
            key="sequential_transition_duration",
            help="转场效果持续的时间"
        )
    with llm_columns[2]:
        st.checkbox(
            label="显示出镜小姐姐水印",
            key="sequential_show_username_watermark",
            value=True,
            help="启用后将在视频左上角显示 '出镜小姐姐：用户名' 水印"
        )
    with llm_columns[3]:
        watermark_position_options = {
            "top_left": "左上角",
            "top_right": "右上角",
            "bottom_left": "左下角",
            "bottom_right": "右下角"
        }
        st.selectbox(
            label="水印位置",
            key="sequential_watermark_position",
            options=list(watermark_position_options.keys()),
            format_func=lambda x: watermark_position_options[x],
            index=0,  # 默认左上角
            help="水印在视频中的位置"
        )

# 封面设置
cover_container = st.container(border=True)
with cover_container:
    st.subheader("封面设置")

    llm_columns = st.columns(3)
    with llm_columns[0]:
        cover_type_options = {"none": "无封面", "4grid": "4宫格封面", "9grid": "9宫格封面"}
        st.radio(
            label="封面类型",
            key="sequential_cover_type",
            options=list(cover_type_options.keys()),
            format_func=lambda x: cover_type_options[x],
            horizontal=True,
            index=1,  # 默认选择"4宫格封面"
            help="视频封面样式（4宫格需要4个视频，9宫格需要9个视频）"
        )
    with llm_columns[1]:
        st.slider(
            label="封面截取时间（秒）",
            min_value=1,
            max_value=10,
            value=2,
            step=1,
            key="sequential_cover_timestamp",
            help="从每个视频的第几秒截取封面帧"
        )
    with llm_columns[2]:
        generated_cover = st.session_state.get("sequential_generated_cover_image")
        if generated_cover and os.path.exists(generated_cover):
            st.image(generated_cover, caption="生成的封面", width=150)

    # 封面文字设置
    text_columns = st.columns(2)
    with text_columns[0]:
        st.text_input(
            label="封面第一行文字",
            key="sequential_cover_line1",
            value="盘点漂亮小姐姐",
            help="封面上的第一行文字"
        )
    with text_columns[1]:
        st.text_input(
            label="封面第二行文字",
            key="sequential_cover_line2",
            value="你最喜欢哪一位",
            help="封面上的第二行文字"
        )

# 生成视频
if "is_generating" not in st.session_state:
    st.session_state["is_generating"] = False

video_generator = st.container(border=True)
with video_generator:
    if st.button(
        "生成视频" if not st.session_state["is_generating"] else "生成中...",
        type="primary",
        key="generate_btn",
        disabled=st.session_state["is_generating"]
    ):
        st.session_state["is_generating"] = True
        main_generate_sequential_merge()
        st.session_state["is_generating"] = False

# 显示结果
result_video = st.session_state.get("sequential_result_video")
if result_video and os.path.exists(result_video):
    st.success("视频生成成功！")
    st.video(result_video)

    # 提供下载链接
    with open(result_video, "rb") as f:
        st.download_button(
            label="下载视频",
            data=f,
            file_name=os.path.basename(result_video),
            mime="video/mp4"
        )

    # 清除结果按钮
    if st.button("清除结果", type="secondary"):
        st.session_state.pop("sequential_result_video", None)
        st.rerun()
