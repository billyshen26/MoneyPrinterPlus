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

from config.config import app_title, load_session_state_from_yaml
from pages.common import common_ui
from services.video.subtitle_cut_service import (
    SubtitleCutService, parse_csv_subtitle, get_video_info,
    seconds_to_hhmmss, parse_timecode_range
)
from tools.utils import get_file_map_from_dir

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

load_session_state_from_yaml('06_subtitle_cut')


common_ui()

st.markdown(f"<h1 style='text-align: center; font-weight:bold; font-family:comic sans ms; padding-top: 0rem;'> \
            {app_title}</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center;padding-top: 0rem;'>电影字幕剪切工具</h2>", unsafe_allow_html=True)


def generate_cut_video():
    """生成剪切视频"""
    video_file = st.session_state.get("source_video_file")
    csv_path = st.session_state.get("subtitle_csv_path")

    if not video_file or not os.path.exists(video_file):
        st.error(f"视频文件不存在: {video_file}")
        return

    if not csv_path or not os.path.exists(csv_path):
        st.error(f"字幕文件不存在: {csv_path}")
        return

    fps = st.session_state.get("cut_video_fps", 30)
    add_subtitle = st.session_state.get("cut_add_subtitle", True)
    max_duration = st.session_state.get("cut_max_duration", 180)

    with cut_container:
        st_area = st.status("正在处理视频...", expanded=True)
        with st_area:
            try:
                # 创建服务
                service = SubtitleCutService(video_file, csv_path, fps, max_duration)

                # 显示剪辑计划
                total_source_duration = sum(s.duration for s in service.segments)
                st.write(f"字幕总时长: {total_source_duration} 秒")
                st.write(f"目标时长: {max_duration} 秒")
                if total_source_duration > max_duration:
                    st.info(f"将自动截取前 {max_duration} 秒的内容")

                # 验证时间码
                st.write("验证时间码...")
                validation = service.validate_timecodes()

                if not validation['valid']:
                    for error in validation['errors']:
                        st.error(error)
                    st_area.update(label="验证失败!", state="error", expanded=False)
                    return

                for warning in validation['warnings']:
                    st.warning(warning)

                # 生成视频
                st.write("正在剪切和拼接视频片段...")
                final_video = service.generate_final_video(
                    add_subtitle=add_subtitle,
                    progress_callback=lambda p: st_area.progress(p)
                )

                if final_video and os.path.exists(final_video):
                    file_size = os.path.getsize(final_video) / (1024 * 1024)  # MB
                    st.session_state["cut_result_video"] = final_video
                    st.session_state["cut_result_size"] = f"{file_size:.2f} MB"
                    st_area.update(label="视频生成完成!", state="complete", expanded=False)
                    st.success(f"✓ 视频已生成: {os.path.basename(final_video)}")
                    st.info(f"📁 文件路径: {final_video}")
                    st.info(f"📊 文件大小: {file_size:.2f} MB")
                    st.rerun()
                elif final_video:
                    # 文件不存在但返回了路径，可能是字幕处理出了问题
                    st.session_state["cut_result_video"] = final_video
                    st.session_state["cut_result_error"] = "视频拼接完成，但字幕可能未添加"
                    st_area.update(label="视频拼接完成（字幕可能有误）", state="warning", expanded=False)
                    st.warning(f"视频文件: {final_video}")
                    st.rerun()
                else:
                    st_area.update(label="视频生成失败!", state="error", expanded=False)

            except Exception as e:
                st.error(f"处理出错: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                st_area.update(label="处理出错!", state="error", expanded=False)


# 视频文件选择
video_input_container = st.container(border=True)
with video_input_container:
    st.subheader("源视频文件")
    
    # 视频目录输入
    default_video_dir = st.session_state.get("cut_video_dir", "D:\\video")
    st.text_input(
        label="视频文件夹路径",
        key="cut_video_dir",
        value=default_video_dir,
        help="输入包含视频文件的文件夹路径"
    )
    
    # 获取视频文件列表
    video_dir = st.session_state.get("cut_video_dir", "")
    video_map = get_file_map_from_dir(video_dir, ".mp4,.mov,.avi,.mkv,.flv,.wmv,.webm")
    
    if video_map:
        # 确保当前选择有效
        current_video = st.session_state.get("cut_source_video")
        if current_video not in video_map:
            st.session_state["cut_source_video"] = list(video_map.keys())[0] if video_map else None
        
        st.selectbox(
            label="选择视频文件",
            key="cut_source_video",
            options=video_map,
            format_func=lambda x: video_map[x]
        )
        
        # 显示选中的视频信息
        selected_video = st.session_state.get("cut_source_video")
        if selected_video and os.path.exists(selected_video):
            st.session_state["source_video_file"] = selected_video
            video_info = get_video_info(selected_video)
            st.session_state["video_info"] = video_info

            col1, col2, col3 = st.columns(3)
            with col1:
                st.success(f"✓ {os.path.basename(selected_video)}")
            with col2:
                st.info(f"时长: {video_info['duration']:.1f}秒")
            with col3:
                st.info(f"分辨率: {video_info['width']}x{video_info['height']}")
    else:
        st.warning(f"文件夹中未找到视频文件: {video_dir}")


# CSV字幕文件选择
csv_input_container = st.container(border=True)
with csv_input_container:
    st.subheader("字幕文件")
    
    st.info("请选择CSV字幕文件，CSV格式：序号,字幕时间轴,时长,对应解说文案,电影原片截取时间码")
    
    # 字幕目录输入
    default_csv_dir = st.session_state.get("cut_csv_dir", "D:\\video")
    st.text_input(
        label="字幕文件夹路径",
        key="cut_csv_dir",
        value=default_csv_dir,
        help="输入包含字幕CSV文件的文件夹路径"
    )
    
    # 获取字幕文件列表
    csv_dir = st.session_state.get("cut_csv_dir", "")
    csv_map = get_file_map_from_dir(csv_dir, ".csv")
    
    if csv_map:
        # 确保当前选择有效
        current_csv = st.session_state.get("cut_subtitle_csv")
        if current_csv not in csv_map:
            st.session_state["cut_subtitle_csv"] = list(csv_map.keys())[0] if csv_map else None
        
        st.selectbox(
            label="选择字幕CSV文件",
            key="cut_subtitle_csv",
            options=csv_map,
            format_func=lambda x: csv_map[x]
        )
        
        # 显示选中的字幕信息
        selected_csv = st.session_state.get("cut_subtitle_csv")
        if selected_csv and os.path.exists(selected_csv):
            st.session_state["subtitle_csv_path"] = selected_csv
            segments = parse_csv_subtitle(selected_csv)
            st.session_state["subtitle_segments"] = segments
            
            if segments:
                st.session_state["subtitle_loaded"] = True
                st.success(f"✓ 字幕文件已加载: {os.path.basename(selected_csv)}")
                st.write(f"共 {len(segments)} 个字幕片段，总时长 {sum(s.duration for s in segments)} 秒")
                
                # 显示字幕预览表格
                import pandas as pd
                preview_data = []
                for seg in segments:
                    source_start, source_end = parse_timecode_range(seg.source_timecode)
                    preview_data.append({
                        "序号": seg.index,
                        "字幕时间": f"{seg.start_time} → {seg.end_time}",
                        "时长": f"{seg.duration}秒",
                        "解说文案": seg.narration[:50] + "..." if len(seg.narration) > 50 else seg.narration,
                        "原片时间码": f"{seconds_to_hhmmss(source_start)} → {seconds_to_hhmmss(source_end)}"
                    })
                
                with st.expander("预览字幕内容", expanded=True):
                    df = pd.DataFrame(preview_data)
                    st.dataframe(df, use_container_width=True)
            else:
                st.session_state["subtitle_loaded"] = False
                st.error("无法解析字幕文件，请检查CSV格式")
    else:
        st.session_state["subtitle_loaded"] = False
        st.warning(f"文件夹中未找到CSV文件: {csv_dir}")


# 视频配置
config_container = st.container(border=True)
with config_container:
    st.subheader("视频配置")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.selectbox(
            label="输出帧率",
            key="cut_video_fps",
            options=[24, 25, 30, 60],
            index=2,
            help="输出视频的帧率"
        )
    
    with col2:
        resolution_options = {
            "1080p": "1080p (1920x1080)", 
            "720p": "720p (1280x720)",
            "4k": "4K (3840x2160)"
        }
        st.selectbox(
            label="输出分辨率",
            key="cut_video_resolution",
            options=resolution_options,
            format_func=lambda x: resolution_options[x],
            help="输出视频的分辨率"
        )
    
    with col3:
        bitrate_options = {
            "低 (2Mbps)": "低 (2Mbps)",
            "中 (5Mbps)": "中 (5Mbps)",
            "高 (10Mbps)": "高 (10Mbps)"
        }
        st.selectbox(
            label="视频码率",
            key="cut_video_bitrate",
            options=bitrate_options,
            format_func=lambda x: bitrate_options[x],
            help="视频码率，越高越清晰但文件越大"
        )

    with col4:
        st.slider(
            label="最大时长(秒)",
            key="cut_max_duration",
            min_value=60,
            max_value=600,
            value=180,
            step=30,
            help="限制最终视频的总时长（秒），默认180秒(3分钟)"
        )

    st.toggle(
        label="添加解说字幕",
        key="cut_add_subtitle",
        value=True,
        help="在视频上添加解说文案作为字幕"
    )


# 字幕样式配置
subtitle_style_container = st.container(border=True)
with subtitle_style_container:
    st.subheader("字幕样式")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.selectbox(
            label="字幕字体",
            key="cut_subtitle_font",
            options=[
                "微软雅黑", "宋体", "黑体", "楷体",
                "Arial", "Helvetica", "Times New Roman"
            ],
            index=0
        )
    
    with col2:
        st.slider(
            label="字体大小",
            min_value=24,
            max_value=72,
            value=48,
            step=2,
            key="cut_subtitle_font_size"
        )
    
    with col3:
        st.selectbox(
            label="字幕位置",
            key="cut_subtitle_position",
            options={
                1: "底部居左",
                2: "底部居中",
                3: "底部居右",
                5: "顶部居左",
                6: "顶部居中",
                7: "顶部居右",
                9: "中间居左",
                10: "中间居中",
                11: "中间居右"
            },
            index=1,
            format_func=lambda x: {1: "底部居左", 2: "底部居中", 3: "底部居右",
                                   5: "顶部居左", 6: "顶部居中", 7: "顶部居右",
                                   9: "中间居左", 10: "中间居中", 11: "中间居右"}[x]
        )
    
    with col4:
        st.slider(
            label="描边宽度",
            min_value=0,
            max_value=6,
            value=3,
            step=1,
            key="cut_subtitle_border_width"
        )
    
    col5, col6 = st.columns(2)
    with col5:
        st.color_picker(
            label="字幕颜色",
            key="cut_subtitle_color",
            value="#FFFFFF"
        )
    
    with col6:
        st.color_picker(
            label="描边颜色",
            key="cut_subtitle_border_color",
            value="#000000"
        )


# 生成视频
cut_container = st.container(border=True)
with cut_container:
    st.subheader("生成视频")
    
    video_ready = st.session_state.get("source_video_file") is not None and os.path.exists(st.session_state.get("source_video_file", ""))
    subtitle_ready = st.session_state.get("subtitle_loaded", False) and len(st.session_state.get("subtitle_segments", [])) > 0
    
    can_generate = video_ready and subtitle_ready
    
    st.button(
        label="开始生成视频",
        type="primary",
        disabled=not can_generate,
        on_click=generate_cut_video
    )
    
    if not can_generate:
        if not video_ready:
            st.warning("请选择有效的电影视频文件")
        if not subtitle_ready:
            st.warning("请选择有效的字幕CSV文件")


# 显示结果
result_video = st.session_state.get("cut_result_video")
if result_video and os.path.exists(result_video):
    st.markdown("---")
    st.subheader("生成结果")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("视频生成完成")
    with col2:
        if st.session_state.get("cut_result_size"):
            st.info(f"大小: {st.session_state['cut_result_size']}")
    with col3:
        if st.button("清空结果"):
            st.session_state.pop("cut_result_video", None)
            st.session_state.pop("cut_result_size", None)
            st.rerun()

    st.info(f"📁 文件路径: `{result_video}`")
    st.info("请直接在该路径下打开视频文件播放")
