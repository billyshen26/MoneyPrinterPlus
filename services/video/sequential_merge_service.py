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
import shutil
import subprocess
import uuid

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from services.video.texiao_service import gen_filter
from services.video.video_service import (
    get_video_duration, get_video_info, get_video_length_list,
    generate_video_cover, create_sequential_intro_video
)
from tools.file_utils import generate_temp_filename
from tools.utils import random_with_system_time, run_ffmpeg_command

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
video_output_dir = os.path.join(script_dir, "../../final")
video_output_dir = os.path.abspath(video_output_dir)
work_output_dir = os.path.join(script_dir, "../../work")
work_output_dir = os.path.abspath(work_output_dir)
tmp_output_dir = os.path.join(script_dir, "../../tmp")
tmp_output_dir = os.path.abspath(tmp_output_dir)
os.makedirs(tmp_output_dir, exist_ok=True)


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


def render_username_image(username, output_path, prefix="出镜小姐姐：", width=500, font_size=48):
    """用 Pillow 把用户名渲染成白字透明底图片，支持前缀"""
    try:
        full_text = f"{prefix}{username}" if prefix else username
        img = Image.new('RGBA', (width, font_size + 24), color=(0, 0, 0, 0))
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
        draw.text((x, y), full_text, fill=(255, 255, 255), font=font, stroke_width=3, stroke_fill=(0, 0, 0))
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

        self.show_username_watermark = st.session_state.get("sequential_show_username_watermark", True)

        # 封面文字
        self.cover_line1 = st.session_state.get("sequential_cover_line1", "盘点漂亮小美女")
        self.cover_line2 = st.session_state.get("sequential_cover_line2", "你最喜欢哪一位")

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

        return final_video

    def _normalize_videos(self):
        """标准化视频尺寸和添加水印，直接截取保持原始质量"""
        print(f"[SequentialMerge] 开始标准化视频，共 {len(self.video_list)} 个")

        normalized_list = []

        for i, video_file in enumerate(self.video_list):
            if not os.path.exists(video_file):
                print(f"视频文件不存在: {video_file}")
                continue

            print(f"[SequentialMerge] 处理第 {i+1}/{len(self.video_list)} 个视频: {os.path.basename(video_file)}")

            output_name = generate_temp_filename(video_file, "_seq.mp4", work_output_dir)

            # 获取视频信息
            video_width, video_height = get_video_info(video_file)

            # 提取用户名作为水印
            username = None
            if self.show_username_watermark:
                username = extract_username_from_filename(video_file)

            # 构建视频滤镜：缩放到目标尺寸，保持高质量
            if video_width / video_height > self.target_width / self.target_height:
                base_scale = f"scale=-1:{self.target_height}:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}"
            else:
                base_scale = f"scale={self.target_width}:-1:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}"

            # 构建完整的滤镜链
            if username:
                username_img = generate_temp_filename(output_name, "_username.png", work_output_dir)
                if render_username_image(username, username_img, prefix="出镜小姐姐：", width=500, font_size=48):
                    # 根据水印位置计算 overlay 坐标
                    if self.watermark_position == "top_left":
                        overlay_pos = "10:80"
                    elif self.watermark_position == "top_right":
                        overlay_pos = "(W-w-10):80"
                    elif self.watermark_position == "top_center":
                        overlay_pos = "(W-w)/2:80"
                    elif self.watermark_position == "bottom_left":
                        overlay_pos = "10:(H-h-10)"
                    else:  # bottom_right
                        overlay_pos = "(W-w-10):(H-h-10)"

                    vf = f"{base_scale},format=yuv420p[out];[out][1:v]overlay={overlay_pos}[out]"
                    command = [
                        'ffmpeg', '-ss', '0',
                        '-i', video_file,
                        '-i', username_img,
                        '-t', str(self.video_duration),
                        '-filter_complex', vf,
                        '-map', '0:a?',
                        '-map', '[out]',
                        '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                        '-c:a', 'aac', '-b:a', '192k',
                        '-r', str(self.fps),
                        '-pix_fmt', 'yuv420p',
                        '-y', output_name
                    ]
                else:
                    command = [
                        'ffmpeg', '-ss', '0',
                        '-i', video_file,
                        '-t', str(self.video_duration),
                        '-vf', f"{base_scale},format=yuv420p",
                        '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                        '-c:a', 'aac', '-b:a', '192k',
                        '-r', str(self.fps),
                        '-pix_fmt', 'yuv420p',
                        '-map', '0:v', '-map', '0:a?',
                        '-y', output_name
                    ]
            else:
                command = [
                    'ffmpeg', '-ss', '0',
                    '-i', video_file,
                    '-t', str(self.video_duration),
                    '-vf', f"{base_scale},format=yuv420p",
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                    '-c:a', 'aac', '-b:a', '192k',
                    '-r', str(self.fps),
                    '-pix_fmt', 'yuv420p',
                    '-map', '0:v', '-map', '0:a?',
                    '-y', output_name
                ]

            print(f"[SequentialMerge] 执行FFmpeg: {os.path.basename(video_file)}")
            run_ffmpeg_command(command)

            if os.path.exists(output_name):
                normalized_list.append(output_name)
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

        # 在拼接之前，为每个视频创建带有顺序介绍镜头的视频
        video_with_intros = self._add_intro_to_videos(video_list)

        if self.transition_type != "none" and len(video_list) > 1:
            print(f"[SequentialMerge] 使用转场特效: {self.transition_type}")
            merge_video = self._concatenate_with_transition(video_with_intros)
        else:
            print("[SequentialMerge] 使用简单拼接")
            merge_video = self._concatenate_simple(video_with_intros)

        if merge_video and os.path.exists(merge_video):
            if self.cover_type != "none":
                self._add_cover(merge_video, video_list)
            else:
                print("[SequentialMerge] 无封面设置，直接输出带介绍镜头的视频")

        return merge_video

    def _add_intro_to_videos(self, video_list):
        """为每个视频添加顺序介绍镜头（黑色背景 + 白色文字 + TTS语音）"""
        print(f"[SequentialMerge] 为 {len(video_list)} 个视频添加顺序介绍镜头")

        video_with_intros = []

        for i, video_file in enumerate(video_list):
            if not os.path.exists(video_file):
                print(f"[SequentialMerge] 视频文件不存在: {video_file}")
                video_with_intros.append(video_file)
                continue

            # 创建顺序介绍镜头
            intro_video = create_sequential_intro_video(
                index=i + 1,  # 第几位（从1开始）
                width=self.target_width,
                height=self.target_height,
                fps=self.fps,
                output_video=os.path.join(tmp_output_dir, f'intro_{i+1}.mp4'),
                output_dir=tmp_output_dir
            )

            if intro_video and os.path.exists(intro_video):
                # 将介绍镜头和视频合并 - 使用 filter_complex 方法
                temp_with_intro = os.path.join(tmp_output_dir, f'video_with_intro_{i+1}.mp4')

                # 使用 filter_complex 拼接
                concat_cmd = [
                    'ffmpeg', '-y',
                    '-i', intro_video,
                    '-i', video_file,
                    '-filter_complex',
                    f'[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]',
                    '-map', '[outv]', '-map', '[outa]',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                    '-c:a', 'aac', '-b:a', '192k',
                    '-r', str(self.fps),
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                    temp_with_intro
                ]

                result = subprocess.run(concat_cmd, capture_output=True, encoding='utf-8', errors='replace')
                if result.returncode == 0 and os.path.exists(temp_with_intro):
                    video_with_intros.append(temp_with_intro)
                else:
                    print(f"[SequentialMerge] 添加介绍镜头失败: {result.stderr[:200] if result.stderr else '未知错误'}")
                    video_with_intros.append(video_file)
            else:
                video_with_intros.append(video_file)

        return video_with_intros

    def _concatenate_simple(self, video_list):
        """简单拼接视频，保留所有视频的声音（依次播放，不混合）"""
        random_name = str(random_with_system_time())
        merge_video = os.path.join(video_output_dir, f"sequential-{random_name}.mp4")

        # 获取视频时长
        video_length_list = get_video_length_list(video_list)
        if not video_length_list:
            print("[SequentialMerge] 无法获取视频时长")
            return None

        total_duration = sum(video_length_list)
        print(f"[SequentialMerge] 简单拼接 {len(video_list)} 个视频，总时长: {total_duration:.1f}秒")

        # 使用 filter_complex 拼接，统一音频格式
        n = len(video_list)
        inputs = []
        for video in video_list:
            inputs.extend(['-i', video])

        # 构建音频重采样和拼接滤镜
        audio_filters = []
        for i in range(n):
            audio_filters.append(f'[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]')
        
        audio_concat = ''.join([f'[a{i}]' for i in range(n)])
        audio_filters.append(f'{audio_concat}concat=n={n}:v=0:a=1[aout]')

        # 视频拼接
        video_concat = ''.join([f'[{i}:v]' for i in range(n)])
        video_concat += f'concat=n={n}:v=1:a=0[outv]'

        filter_complex = ';'.join(audio_filters) + ';' + video_concat

        command = [
            'ffmpeg', '-y',
            *inputs,
            '-filter_complex', filter_complex,
            '-map', '[outv]',
            '-map', '[aout]',
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
            '-c:a', 'aac', '-b:a', '192k',
            '-ar', '44100',
            '-ac', '2',
            '-r', str(self.fps),
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            merge_video
        ]

        print(f"[SequentialMerge] 拼接命令: ffmpeg filter_complex (依次播放音频)...")
        result = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"[SequentialMerge] 简单拼接失败: {result.stderr[:500]}")

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

        # 使用高质量编码参数
        command = ['ffmpeg', *itertools.chain(*files_input),
                   '-filter_complex', zhuanchang_txt,
                   '-map', '[video]',
                   '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                   '-c:a', 'aac', '-b:a', '192k',
                   '-r', str(self.fps),
                   '-pix_fmt', 'yuv420p',
                   '-movflags', '+faststart',
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

        import uuid
        random_name = str(uuid.uuid4())[:8]

        cover_image = None
        cover_video = None

        # 封面生成在tmp目录，避免final目录出现中间文件
        if self.cover_type == "4grid" and len(video_list) >= 4:
            cover_image, cover_video = generate_video_cover(
                video_list[:4],
                tmp_output_dir,
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
                tmp_output_dir,
                self.target_width,
                self.target_height,
                self.fps,
                self.cover_timestamp,
                self.cover_line1,
                self.cover_line2
            )

        if cover_video and os.path.exists(cover_video):
            # 封面视频在tmp目录，需要将合并视频移到tmp，拼接后再移回final目录
            temp_merge = os.path.join(tmp_output_dir, 'temp_merged_video.mp4')
            if os.path.exists(merge_video):
                shutil.move(merge_video, temp_merge)

                # 使用 filter_complex 拼接封面和视频，统一音频格式（依次播放）
                concat_cmd = [
                    'ffmpeg', '-y',
                    '-i', cover_video,
                    '-i', temp_merge,
                    '-filter_complex', '[0:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a0];[1:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[a1];[a0][a1]concat=n=2:v=0:a=1[aout];[0:v][1:v]concat=n=2:v=1:a=0[outv]',
                    '-map', '[outv]',
                    '-map', '[aout]',
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                    '-c:a', 'aac', '-b:a', '192k',
                    '-ar', '44100',
                    '-ac', '2',
                    '-r', str(self.fps),
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                    merge_video
                ]

                print(f"[SequentialMerge] 封面拼接命令: ffmpeg filter_complex (依次播放音频)...")
                subprocess.run(concat_cmd, capture_output=True, encoding='utf-8', errors='replace')

                # 清理临时文件
                if os.path.exists(temp_merge):
                    os.remove(temp_merge)
                if os.path.exists(cover_video):
                    os.remove(cover_video)
                if cover_image and os.path.exists(cover_image):
                    os.remove(cover_image)

                if cover_image:
                    st.session_state["sequential_generated_cover_image"] = None  # 封面已删除
                print(f"[SequentialMerge] 封面已添加到视频")
