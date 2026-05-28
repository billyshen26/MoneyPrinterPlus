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
import time

import pandas as pd
import streamlit as st

from config.config import app_title
from pages.common import common_ui
from services.subtitle.subtitle_generator_service import SubtitleGeneratorService, SubtitleSegment

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)

common_ui()

st.markdown(f"<h1 style='text-align: center; font-weight:bold; font-family:comic sans ms; padding-top: 0rem;'> \
            {app_title}</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center;padding-top: 0rem;'>AI字幕生成器</h2>", unsafe_allow_html=True)

# 初始化服务
def get_generator_service():
    return SubtitleGeneratorService()


def seconds_to_hhmmss(seconds: int) -> str:
    """将秒数转换为 HH:MM:SS 格式"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_duration(duration_str: str) -> int:
    """解析时长字符串"""
    duration_str = str(duration_str).replace('秒', '').strip()
    try:
        return int(float(duration_str))
    except:
        return 20


# 输入区域
input_container = st.container(border=True)
with input_container:
    st.subheader("输入参数")

    col1, col2 = st.columns(2)
    with col1:
        movie_name = st.text_input(
            label="电影/视频名称",
            placeholder="例如：泰坦尼克号",
            help="输入你想要生成解说字幕的电影或视频名称"
        )

        style = st.selectbox(
            label="解说风格",
            options=[
                "感人煽情",
                "震撼大片",
                "知识科普",
                "悬疑紧张",
                "轻松幽默",
                "热血激昂",
                "抒情文艺"
            ],
            help="选择解说文案的整体风格"
        )

    with col2:
        total_duration = st.slider(
            label="总时长（秒）",
            min_value=30,
            max_value=600,
            value=180,
            step=30,
            help="生成的视频总时长，默认180秒（3分钟）"
        )

        language = st.selectbox(
            label="回复语言",
            options=["中文", "英文", "日文", "韩文"],
            help="AI回复的语言"
        )

    # 剪辑要求输入
    custom_requirements = st.text_area(
        label="剪辑要求（可选）",
        placeholder="例如：请挑选电影中最精彩的10个片段，每个片段25秒左右，重点展示动作场面和情感高潮...",
        help="输入你的剪辑要求，LLM会根据这些要求来生成解说文案和选择原片时间码"
    )

    # 生成按钮
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        generate_clicked = st.button("生成字幕", type="primary", use_container_width=True)

# 生成逻辑
if generate_clicked and movie_name:
    if 'subtitle_generator' not in st.session_state:
        st.session_state['subtitle_generator'] = get_generator_service()

    generator = st.session_state['subtitle_generator']

    status_area = st.info(f"正在为《{movie_name}》生成字幕（风格：{style}，时长：{total_duration}秒）...")

    try:
        segments = generator.generate_subtitle(
            movie_name=movie_name,
            total_duration=total_duration,
            style=style,
            language=language,
            custom_requirements=custom_requirements if custom_requirements else None
        )
        st.session_state['generated_segments'] = segments
        st.session_state['movie_name'] = movie_name
        st.success(f"成功生成 {len(segments)} 个字幕片段！总时长约 {sum(s.duration for s in segments)} 秒")
    except Exception as e:
        st.error(f"生成失败: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

elif generate_clicked and not movie_name:
    st.warning("请输入电影/视频名称")

# 字幕编辑区域
if 'generated_segments' in st.session_state and st.session_state['generated_segments']:
    segments = st.session_state['generated_segments']

    edit_container = st.container(border=True)
    with edit_container:
        st.subheader("字幕编辑")

        # 统计信息
        total_dur = sum(s.duration for s in segments)
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("片段数量", len(segments))
        with col_stat2:
            st.metric("总时长", f"{total_dur}秒")
        with col_stat3:
            st.metric("平均每段", f"{total_dur // len(segments)}秒")

        st.markdown("---")

        # 转换为 DataFrame 用于编辑
        df_data = []
        for seg in segments:
            df_data.append({
                "序号": seg.index,
                "开始时间": seg.start_time,
                "结束时间": seg.end_time,
                "时长(秒)": seg.duration,
                "解说文案": seg.narration,
                "原片时间码": seg.source_timecode
            })

        df = pd.DataFrame(df_data)

        # 使用 data_editor 进行编辑
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "序号": st.column_config.NumberColumn("序号", disabled=True),
                "开始时间": st.column_config.TextColumn("开始时间", disabled=True),
                "结束时间": st.column_config.TextColumn("结束时间", disabled=True),
                "时长(秒)": st.column_config.NumberColumn("时长(秒)", min_value=1, max_value=300),
                "解说文案": st.column_config.TextColumn(
                    "解说文案",
                    width="large",
                    help="可编辑的解说文案"
                ),
                "原片时间码": st.column_config.TextColumn(
                    "原片时间码",
                    help="格式: 00:00:00 → 00:00:20"
                )
            },
            key="subtitle_editor"
        )

        # 检测变化并更新 session_state
        if edited_df is not None:
            # 重新计算时间轴
            current_time = 0
            updated_segments = []
            for idx, row in edited_df.iterrows():
                duration = int(row['时长(秒)'])
                end_time = current_time + duration

                # 解析原片时间码
                source_timecode = row['原片时间码']

                segment = SubtitleSegment(
                    index=int(row['序号']),
                    start_time=seconds_to_hhmmss(current_time),
                    end_time=seconds_to_hhmmss(end_time),
                    duration=duration,
                    narration=row['解说文案'],
                    source_timecode=source_timecode
                )
                updated_segments.append(segment)
                current_time = end_time

            st.session_state['generated_segments'] = updated_segments

            # 显示更新后的总时长
            new_total = sum(s.duration for s in updated_segments)
            if new_total != total_dur:
                st.info(f"已更新，总时长: {new_total} 秒")

        st.markdown("---")

        # 操作按钮
        col_act1, col_act2, col_act3, col_act4 = st.columns(4)

        with col_act1:
            if st.button("重新生成", use_container_width=True):
                st.rerun()

        with col_act2:
            # 添加片段
            if st.button("添加片段", use_container_width=True):
                last_seg = segments[-1]
                new_seg = SubtitleSegment(
                    index=len(segments) + 1,
                    start_time=last_seg.end_time,
                    end_time=seconds_to_hhmmss(
                        sum(s.duration for s in segments) + 20
                    ),
                    duration=20,
                    narration="新片段的解说文案...",
                    source_timecode="00:00:00 → 00:00:20"
                )
                segments.append(new_seg)
                st.session_state['generated_segments'] = segments
                st.rerun()

        with col_act3:
            # 删除选中片段（通过序号）
            delete_idx = st.number_input(
                "删除片段序号",
                min_value=1,
                max_value=len(segments),
                value=len(segments),
                step=1,
                help="输入要删除的片段序号"
            )
            if st.button("删除片段", use_container_width=True):
                # 重新编号
                segments = [s for s in segments if s.index != delete_idx]
                for i, seg in enumerate(segments, 1):
                    seg.index = i
                st.session_state['generated_segments'] = segments
                st.rerun()

        with col_act4:
            # 导出CSV
            default_output_dir = os.path.join(script_dir, "../srt")
            output_dir = st.text_input(
                "输出目录",
                value=default_output_dir,
                help="CSV文件保存目录"
            )
            output_filename = st.text_input(
                "文件名",
                value=f"subtitle_{int(time.time())}.csv",
                help="CSV文件名"
            )
            output_path = os.path.join(output_dir, output_filename)
            if st.button("导出CSV", use_container_width=True):
                generator = st.session_state.get('subtitle_generator')
                if generator:
                    # 确保目录存在
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    generator.export_to_csv(segments, output_path)
                    st.success(f"已导出到: {output_path}")

                    # 提供下载按钮
                    with open(output_path, 'r', encoding='utf-8') as f:
                        st.download_button(
                            label="下载CSV文件",
                            data=f,
                            file_name=os.path.basename(output_path),
                            mime="text/csv"
                        )

# 说明区域
if 'generated_segments' not in st.session_state or not st.session_state.get('generated_segments'):
    st.info("""
    ## 使用说明

    1. **输入参数**：输入电影/视频名称，选择解说风格和总时长
    2. **生成字幕**：点击"生成字幕"按钮，AI将自动生成解说文案和字幕切分
    3. **微调编辑**：在表格中修改解说文案、原片时间码等
    4. **导出使用**：导出为CSV文件，可用于电影剪切功能

    ### 原片时间码格式
    - 格式：`00:00:00 → 00:00:20`
    - 表示：电影原片从几分几秒到几分几秒
    - 建议：根据电影情节选择合适的片段位置
    """)
