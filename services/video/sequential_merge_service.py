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
import random
import re
import subprocess
import uuid

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from services.video.originality_service import OriginalityService
from services.video.texiao_service import gen_filter
from services.video.video_service import (
    get_video_duration, get_video_info, get_video_length_list,
    add_background_music, generate_video_cover
)
from tools.file_utils import generate_temp_filename
from tools.utils import random_with_system_time, run_ffmpeg_command

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
video_output_dir = os.path.join(script_dir, "../../final")
video_output_dir = os.path.abspath(video_output_dir)
work_output_dir = os.path.join(script_dir, "../../work")
work_output_dir = os.path.abspath(work_output_dir)


def get_video_files_from_folder(folder_path):
    """获取文件夹中所有视频文件"""
    if not folder_path or not os.path.exists(folder_path):
        return []

    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm')
    video_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith(video_extensions)
    ]
    video_files.sort()
    return video_files


def extract_username_from_filename(filename):
    """从文件名中提取用户名，格式: fav_用户名_ID.mp4"""
    basename = os.path.basename(filename)
    m = re.match(r'fav_(.+?)_\d+\.mp4$', basename)
    if m:
        return m.group(1)
    return None


def render_username_image(username, output_path, prefix="出镜小姐姐：", width=500, font_size=36):
    """用 Pillow 把用户名渲染成白字透明底图片，支持前缀"""
    try:
        full_text = f"{prefix}{username}" if prefix else username
        img = Image.new('RGBA', (width, font_size + 20), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = None
        for fp in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/simsun.ttc']:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, font_size)
                break
        if font is None:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), full_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = 10
        y = 8
        draw.text((x, y), full_text, fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
        img.save(output_path)
        return True
    except Exception as e:
        print(f"渲染用户名图片失败: {e}")
        return False


class SequentialMergeService:
    """顺序拼接视频服务"""

    def __init__(self, video_list, transition_type="xfade", transition_duration=1.0,
                 watermark_text=None, watermark_position="bottom_right",
                 cover_type="4grid", cover_timestamp=2, video_folder=None,
                 video_duration=10):
        self.video_list = video_list
        self.transition_type = transition_type
        self.transition_duration = transition_duration
        self.watermark_text = watermark_text
        self.watermark_position = watermark_position
        self.cover_type = cover_type
        self.cover_timestamp = cover_timestamp
        self.video_folder = video_folder
        self.video_duration = video_duration

        self.fps = st.session_state.get("sequential_video_fps", 30)
        video_size = st.session_state.get("sequential_video_size", "1080x1920")
        self.target_width, self.target_height = video_size.split('x')
        self.target_width = int(self.target_width)
        self.target_height = int(self.target_height)

        self.enable_background_music = st.session_state.get("sequential_enable_background_music", False)
        self.background_music = st.session_state.get("sequential_background_music", "")
        self.background_music_volume = st.session_state.get("sequential_background_music_volume", 0.3)

        self.enable_originality = st.session_state.get("sequential_enable_originality", True)
        self.filter_preset = st.session_state.get("sequential_filter_preset", "light")
        self.show_username_watermark = st.session_state.get("sequential_show_username_watermark", True)

        # 封面文字
        self.cover_line1 = st.session_state.get("sequential_cover_line1", "盘点漂亮小姐姐")
        self.cover_line2 = st.session_state.get("sequential_cover_line2", "你最喜欢哪一位")

        self.originality_service = OriginalityService(work_output_dir)

    def process_videos(self):
        """主处理流程"""
        if not self.video_list or len(self.video_list) < 2:
            print("视频列表为空或数量不足")
            return None

        print(f"[SequentialMerge] 开始处理 {len(self.video_list)} 个视频")

        normalized_videos = self._normalize_videos()

        if not normalized_videos:
            print("视频标准化失败")
            return None

        final_video = self._concatenate_videos(normalized_videos)

        if final_video and self.enable_background_music and self.background_music:
            add_background_music(final_video, self.background_music, self.background_music_volume)

        return final_video

    def _normalize_videos(self):
        """标准化视频尺寸和添加水印"""
        print(f"[SequentialMerge] 开始标准化视频，共 {len(self.video_list)} 个")

        normalized_list = []

        for i, video_file in enumerate(self.video_list):
            if not os.path.exists(video_file):
                print(f"视频文件不存在: {video_file}")
                continue

            print(f"[SequentialMerge] 处理第 {i+1}/{len(self.video_list)} 个视频: {os.path.basename(video_file)}")

            output_name = generate_temp_filename(video_file, "_seq.mp4", work_output_dir)

            video_width, video_height = get_video_info(video_file)

            if video_width / video_height > self.target_width / self.target_height:
                base_scale = f"scale=-1:{self.target_height}:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2"
            else:
                base_scale = f"scale={self.target_width}:-1:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2"

            username = None
            if self.show_username_watermark:
                username = extract_username_from_filename(video_file)

            if username:
                username_img = generate_temp_filename(output_name, "_username.png", work_output_dir)
                if render_username_image(username, username_img, prefix="出镜小姐姐：", width=500, font_size=36):
                    # 根据水印位置计算 overlay 坐标
                    if self.watermark_position == "top_left":
                        overlay_pos = "10:10"
                    elif self.watermark_position == "top_right":
                        overlay_pos = "(W-w-10):10"
                    elif self.watermark_position == "bottom_left":
                        overlay_pos = "10:(H-h-10)"
                    else:  # bottom_right
                        overlay_pos = "(W-w-10):(H-h-10)"

                    vf = f"{base_scale},format=yuv420p[out];[out][1:v]overlay={overlay_pos}[out]"
                    command = [
                        'ffmpeg', '-i', video_file,
                        '-i', username_img,
                        '-filter_complex', vf,
                        '-map', '0:a?',
                        '-map', '[out]',
                        '-r', str(self.fps),
                        '-y', output_name
                    ]
                else:
                    command = [
                        'ffmpeg', '-i', video_file,
                        '-vf', base_scale,
                        '-r', str(self.fps),
                        '-map', '0:v',
                        '-map', '0:a?',
                        '-y', output_name
                    ]
            else:
                command = [
                    'ffmpeg', '-i', video_file,
                    '-vf', base_scale,
                    '-r', str(self.fps),
                    '-map', '0:v',
                    '-map', '0:a?',
                    '-y', output_name
                ]

            print(f"[SequentialMerge] 执行FFmpeg: {os.path.basename(video_file)}")
            run_ffmpeg_command(command)

            if os.path.exists(output_name):
                processed_file = self.originality_service.process_video(
                    output_name,
                    enable_random_start=self.enable_originality,
                    filter_preset=self.filter_preset,
                    max_duration=self.video_duration
                )
                normalized_list.append(processed_file)
            else:
                print(f"[SequentialMerge] FFmpeg输出文件未生成: {output_name}")

        return normalized_list

    def _concatenate_videos(self, video_list):
        """拼接视频，支持转场效果"""
        print(f"[SequentialMerge] 开始拼接视频，共 {len(video_list)} 个")

        if len(video_list) < 2:
            return video_list[0] if video_list else None

        random_name = str(random_with_system_time())
        merge_video = os.path.join(video_output_dir, f"sequential-{random_name}.mp4")

        if self.transition_type != "none" and len(video_list) > 1:
            print(f"[SequentialMerge] 使用转场特效: {self.transition_type}")
            merge_video = self._concatenate_with_transition(video_list)
        else:
            print("[SequentialMerge] 使用简单拼接")
            merge_video = self._concatenate_simple(video_list)

        if merge_video and os.path.exists(merge_video) and self.cover_type != "none":
            self._add_cover(merge_video, video_list)

        return merge_video

    def _concatenate_simple(self, video_list):
        """简单拼接视频"""
        random_name = str(random_with_system_time())
        merge_video = os.path.join(video_output_dir, f"sequential-{random_name}.mp4")
        temp_filelist_path = os.path.join(video_output_dir, f'seq_file_list_{random_name}.txt')

        with open(temp_filelist_path, 'w', encoding='utf-8') as f:
            for video_file in video_list:
                f.write(f"file '{video_file}'\n")

        command = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', temp_filelist_path,
            '-c:v', 'libx264', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '128k',
            '-r', str(self.fps),
            '-y', merge_video
        ]

        print(f"[SequentialMerge] 简单拼接命令: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"[SequentialMerge] 简单拼接失败: {result.stderr}")

        if os.path.exists(temp_filelist_path):
            os.remove(temp_filelist_path)

        return merge_video if os.path.exists(merge_video) else None

    def _concatenate_with_transition(self, video_list):
        """使用转场效果拼接视频"""
        import itertools

        random_name = str(random_with_system_time())
        merge_video = os.path.join(video_output_dir, f"sequential-{random_name}.mp4")

        video_length_list = get_video_length_list(video_list)

        transition_value_map = {
            "fade": 0.5,
            "rectblur": 1.0,
            "wiperight": 0.5,
            "wipeleft": 0.5,
            "wipeup": 0.5,
            "wipedown": 0.5,
            "slideleft": 1.0,
            "slideright": 1.0,
            "slideup": 1.0,
            "slidedown": 1.0
        }
        transition_value = transition_value_map.get(self.transition_type, 0.5)

        zhuanchang_txt = gen_filter(
            video_length_list, self.target_width, self.target_height,
            self.transition_type, transition_value, self.transition_duration, False
        )

        files_input = [['-i', f] for f in video_list]

        command = ['ffmpeg', *itertools.chain(*files_input),
                   '-filter_complex', zhuanchang_txt,
                   '-map', '[video]',
                   '-c:v', 'libx264', '-preset', 'fast',
                   '-r', str(self.fps),
                   '-y', merge_video]

        print(f"[SequentialMerge] 转场拼接命令: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"[SequentialMerge] 转场拼接失败: {result.stderr}")
            return self._concatenate_simple(video_list)

        return merge_video if os.path.exists(merge_video) else None

    def _add_cover(self, merge_video, video_list):
        """添加封面"""
        print(f"[SequentialMerge] 添加封面: {self.cover_type}")

        cover_image = None
        cover_video = None

        if self.cover_type == "4grid" and len(video_list) >= 4:
            cover_image, cover_video = generate_video_cover(
                video_list[:4],
                video_output_dir,
                self.target_width,
                self.target_height,
                self.fps,
                self.cover_timestamp,
                self.cover_line1,
                self.cover_line2
            )
        elif self.cover_type == "9grid" and len(video_list) >= 9:
            cover_image, cover_video = generate_video_cover(
                video_list[:9],
                video_output_dir,
                self.target_width,
                self.target_height,
                self.fps,
                self.cover_timestamp,
                self.cover_line1,
                self.cover_line2
            )

        if cover_video and os.path.exists(cover_video):
            temp_merge = merge_video.replace('.mp4', '_no_cover.mp4')
            if os.path.exists(merge_video):
                os.rename(merge_video, temp_merge)

                concat_file = temp_merge.replace('.mp4', '_concat.txt')
                with open(concat_file, 'w') as f:
                    f.write(f"file '{cover_video}'\n")
                    f.write(f"file '{temp_merge}'\n")

                concat_cmd = [
                    'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_file,
                    '-c:v', 'libx264', '-preset', 'fast',
                    '-c:a', 'aac', '-b:a', '128k',
                    '-r', str(self.fps),
                    '-y', merge_video
                ]

                print(f"[SequentialMerge] 封面拼接命令: {' '.join(concat_cmd)}")
                subprocess.run(concat_cmd, capture_output=True, encoding='utf-8', errors='replace')

                if os.path.exists(concat_file):
                    os.remove(concat_file)
                if os.path.exists(temp_merge):
                    os.remove(temp_merge)

                if cover_image:
                    st.session_state["sequential_generated_cover_image"] = cover_image
                print(f"[SequentialMerge] 封面已添加到视频")
