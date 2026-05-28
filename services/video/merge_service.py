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

import itertools
import os
import random
import re
import subprocess
from datetime import timedelta

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from services.captioning.captioning_service import add_subtitles
from services.hunjian.hunjian_service import get_session_video_scene_text, get_video_scene_text_list
from services.video.originality_service import OriginalityService
from services.video.texiao_service import gen_filter
from services.video.video_service import DEFAULT_DURATION, get_image_info, get_video_duration, get_video_info, \
    get_video_length_list, add_background_music
from tools.file_utils import generate_temp_filename
from tools.tr_utils import tr
from tools.utils import run_ffmpeg_command, random_with_system_time

# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)
# 视频出目录
video_output_dir = os.path.join(script_dir, "../../final")
video_output_dir = os.path.abspath(video_output_dir)

# work目录
work_output_dir = os.path.join(script_dir, "../../work")
work_output_dir = os.path.abspath(work_output_dir)


def extract_username_from_filename(filename):
    """从文件名中提取用户名，格式: fav_用户名_ID.mp4"""
    basename = os.path.basename(filename)
    m = re.match(r'fav_(.+?)_\d+\.mp4$', basename)
    if m:
        return m.group(1)
    return None


def render_username_image(username, output_path, width=300, font_size=28):
    """用 Pillow 把用户名渲染成白字透明底图片"""
    try:
        img = Image.new('RGBA', (width, font_size + 20), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = None
        for fp in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/simsun.ttc']:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, font_size)
                break
        if font is None:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), username, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (width - text_w) // 2
        y = 4
        draw.text((x, y), username, fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
        img.save(output_path)
        return True
    except Exception as e:
        print(f"渲染用户名图片失败: {e}")
        return False


def merge_generate_subtitle(video_scene_video_list, video_scene_text_list):
    enable_subtitles = st.session_state.get("enable_subtitles")
    if enable_subtitles and video_scene_text_list is not None:
        st.write(tr("Add Subtitles..."))
        for video_file, scene_text in zip(video_scene_video_list, video_scene_text_list):
            if scene_text is not None and scene_text != "":
                generate_subtitles(video_file, scene_text)


def generate_subtitles(video_file, scene_text):
    # 获取视频时长
    video_duration = get_video_duration(video_file)
    # 生成字幕文件
    # 设置输出字幕
    random_name = random_with_system_time()
    captioning_output = os.path.join(work_output_dir, f"{random_name}.srt")
    subtitle_file = generate_temp_filename(captioning_output)
    gen_subtitle_file(subtitle_file, scene_text, video_duration)
    # 添加字幕

    font_name = st.session_state.get('subtitle_font')
    font_size = st.session_state.get('subtitle_font_size')
    primary_colour = st.session_state.get('subtitle_color')
    outline_colour = st.session_state.get('subtitle_border_color')
    outline = st.session_state.get('subtitle_border_width')
    alignment = st.session_state.get('subtitle_position')
    add_subtitles(video_file, subtitle_file,
                  font_name=font_name,
                  font_size=font_size,
                  primary_colour=primary_colour,
                  outline_colour=outline_colour,
                  outline=outline,
                  alignment=alignment)
    print("file with subtitle:", video_file)


def format_time(seconds):
    """格式化时间为 SRT 字幕格式"""
    time = str(timedelta(seconds=seconds))
    if '.' in time:
        time, milliseconds = time.split('.')
        milliseconds = int(milliseconds) * 1000
    else:
        milliseconds = 0
    return f"{time},000" if milliseconds == 0 else f"{time},{milliseconds:03d}"


def gen_subtitle_file(subtitle_file, scene_text, video_duration):
    """生成 SRT 字幕文件"""
    start_time = 0
    end_time = video_duration

    with open(subtitle_file, 'w', encoding='utf-8') as file:
        file.write("1\n")
        file.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
        file.write(f"{scene_text}\n")
        file.write("\n")


def merge_get_video_list():
    print("merge_get_video_list begin")
    video_dir_list, video_text_list = get_session_video_scene_text()
    video_scene_text_list =[]
    if video_text_list is not None:
        video_scene_text_list = get_video_scene_text_list(video_text_list)
    video_scene_video_list = get_video_scene_video_list(video_dir_list)
    return video_scene_video_list, video_scene_text_list


def get_video_scene_video_list(video_dir_list):
    video_scene_video_list = []
    for video_dir in video_dir_list:
        if video_dir is not None:
            video_file = random_video_from_dir(video_dir)
            video_scene_video_list.append(video_file)
    return video_scene_video_list


def random_video_from_dir(video_dir):
    # 获取媒体文件夹中的所有图片和视频文件
    media_files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if
                   f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov'))]

    # 随机排序媒体文件
    random.shuffle(media_files)

    # 确保有视频文件在列表中
    video_files = [os.path.join(video_dir, f) for f in media_files if f.lower().endswith(('.mp4', '.mov'))]
    if video_files:
        # 从视频文件中随机选择一个
        return random.choice(video_files)

    # 如果没有视频文件，返回随机选择的图片
    return random.choice(media_files) if media_files else None


def get_all_videos_from_folder(video_folder):
    """获取文件夹中所有视频文件，按文件名排序"""
    if not video_folder or not os.path.exists(video_folder):
        return []

    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm')
    video_files = [
        os.path.join(video_folder, f)
        for f in os.listdir(video_folder)
        if f.lower().endswith(video_extensions)
    ]
    video_files.sort()
    return video_files


def get_random_videos_from_folder(video_folder, count, used_videos=None, allow_reuse=False):
    """从文件夹中随机选择指定数量的视频

    Args:
        video_folder: 视频文件夹路径
        count: 需要选择的视频数量
        used_videos: 已使用的视频列表（绝对路径）
        allow_reuse: 是否允许重复使用视频

    Returns:
        随机选择的视频列表
    """
    all_videos = get_all_videos_from_folder(video_folder)
    if not all_videos:
        return []

    if used_videos is None:
        used_videos = []

    if allow_reuse:
        # 允许重复时，直接随机选择
        import random
        return random.sample(all_videos, min(count, len(all_videos)))

    # 不允许重复时，排除已使用的视频
    available_videos = [v for v in all_videos if v not in used_videos]

    # 如果可用视频不够，返回所有可用视频（可能少于要求的数量）
    if len(available_videos) < count:
        # 如果可用视频数量不足，随机返回可用的
        import random
        return random.sample(available_videos, len(available_videos)) if available_videos else []

    # 随机选择
    import random
    return random.sample(available_videos, count)


class VideoMergeService:
    def __init__(self, video_list):
        self.video_list = video_list
        self.fps = st.session_state["video_fps"]
        self.target_width, self.target_height = st.session_state["video_size"].split('x')
        self.target_width = int(self.target_width)
        self.target_height = int(self.target_height)

        self.enable_background_music = st.session_state["enable_background_music"]
        self.background_music = st.session_state["background_music"]
        self.background_music_volume = st.session_state["background_music_volume"]

        self.enable_video_transition_effect = st.session_state["enable_video_transition_effect"]
        self.video_transition_effect_duration = st.session_state["video_transition_effect_duration"]
        self.video_transition_effect_type = st.session_state["video_transition_effect_type"]
        self.video_transition_effect_value = st.session_state["video_transition_effect_value"]
        self.default_duration = DEFAULT_DURATION

        # 原创性提升配置
        self.enable_originality = st.session_state.get("enable_video_originality", True)
        
        # 随机起点截取
        self.random_start_max_offset = st.session_state.get("video_random_start_max_offset", 2.0)
        self.random_start_max_duration = st.session_state.get("video_random_start_max_duration", 5.0)
        
        # 变速处理
        self.enable_speed_change = st.session_state.get("enable_speed_change", False)
        self.speed_range_min = st.session_state.get("speed_range_min", 0.92)
        self.speed_range_max = st.session_state.get("speed_range_max", 1.08)
        
        # 镜像翻转
        self.enable_mirror = st.session_state.get("enable_mirror", False)
        self.mirror_direction = st.session_state.get("mirror_direction", "horizontal")
        
        # 随机缩放
        self.enable_random_crop = st.session_state.get("enable_random_crop", False)
        self.crop_scale_min = st.session_state.get("crop_scale_min", 0.95)
        self.crop_scale_max = st.session_state.get("crop_scale_max", 1.05)
        
        # 噪点
        self.enable_noise = st.session_state.get("enable_noise", False)
        self.noise_intensity = st.session_state.get("noise_intensity", 15)
        
        # 速度渐变
        self.enable_speed_ramp = st.session_state.get("enable_speed_ramp", False)
        self.speed_ramp_type = st.session_state.get("speed_ramp_type", "ease_in_out")
        
        # 滤镜
        self.filter_preset = st.session_state.get("video_filter_preset", "none")
        
        # 水印
        self.enable_watermark = st.session_state.get("enable_watermark", False)
        self.watermark_path = st.session_state.get("video_watermark_path", "")
        self.watermark_position = st.session_state.get("video_watermark_position", "bottom_right")
        self.watermark_opacity = st.session_state.get("video_watermark_opacity", 0.7)
        self.watermark_scale = st.session_state.get("video_watermark_scale", 0.15)
        
        # 音频处理
        self.remove_original_audio = st.session_state.get("remove_original_audio", False)
        self.new_bgm_dir = st.session_state.get("new_bgm_dir", "")
        
        # 自动封面配置
        self.enable_auto_cover = st.session_state.get("enable_auto_cover", False)
        self.cover_timestamp = st.session_state.get("cover_timestamp", 2.0)
        
        # 用户名显示配置
        self.show_username = st.session_state.get("show_video_username", True)
        
        # 创建原创性服务
        self.originality_service = OriginalityService(work_output_dir)

    def normalize_video(self):
        print(f"[DEBUG] ========== 开始normalize_video ==========")
        print(f"[DEBUG] 输入视频列表共 {len(self.video_list)} 个:")
        for i, v in enumerate(self.video_list):
            if v:
                exists = os.path.exists(v)
                print(f"[DEBUG]   [{i+1}] {v} (存在: {exists})")
        
        return_video_list = []
        
        # 保存原始视频列表用于生成封面
        original_video_list = [f for f in self.video_list 
                              if not f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        # 生成4宫格封面
        cover_video = None
        if self.enable_auto_cover:
            print(f"[DEBUG] 自动封面已启用，视频数量: {len(original_video_list)}")
        if self.enable_auto_cover and len(original_video_list) >= 4:
            from services.video.video_service import generate_video_cover
            print(f"[DEBUG] 开始生成4宫格封面...")
            cover_image, cover_video = generate_video_cover(
                original_video_list, 
                video_output_dir,
                self.target_width, 
                self.target_height,
                self.fps,
                self.cover_timestamp
            )
            if cover_image:
                st.session_state["generated_cover_image"] = cover_image
                print(f"[DEBUG] 封面图片已生成: {cover_image}")
            else:
                print(f"[WARNING] 封面图片生成失败")
        elif self.enable_auto_cover and len(original_video_list) < 4:
            print(f"[DEBUG] 视频数量不足4个，当前只有 {len(original_video_list)} 个视频，跳过封面生成")
        
        for media_file in self.video_list:
            # 如果当前文件是图片，添加转换为视频的命令
            if media_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                output_name = generate_temp_filename(media_file, ".mp4", work_output_dir)
                # 判断图片的纵横比和
                img_width, img_height = get_image_info(media_file)
                if img_width / img_height > self.target_width / self.target_height:
                    # 转换图片为视频片段 图片的视频帧率必须要跟视频的帧率一样，否则可能在最后的合并过程中导致 合并过后的视频过长
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-loop', '1',
                        '-i', media_file,
                        '-c:v', 'h264',
                        '-t', str(self.default_duration),
                        '-r', str(self.fps),
                        '-vf',
                        f'scale=-1:{self.target_height}:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2'
                        '-y', output_name]
                else:
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-loop', '1',
                        '-i', media_file,
                        '-c:v', 'h264',
                        '-t', str(self.default_duration),
                        '-r', str(self.fps),
                        '-vf',
                        f'scale={self.target_width}:-1:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2'
                        '-y', output_name]
                print(" ".join(ffmpeg_cmd))
                subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
                return_video_list.append(output_name)

            else:
                # 当前文件是视频文件
                video_duration = get_video_duration(media_file)
                video_width, video_height = get_video_info(media_file)
                output_name = generate_temp_filename(media_file, new_directory=work_output_dir)
                
                # 提取用户名
                username = extract_username_from_filename(media_file) if self.show_username else None
                
                # 构建视频滤镜
                print(f"[DEBUG] 正在处理视频: {media_file}")
                print(f"[DEBUG] 原始视频信息 - 宽度: {video_width}, 高度: {video_height}, 时长: {video_duration}")
                
                if video_width / video_height > self.target_width / self.target_height:
                    base_scale = f"scale=-1:{self.target_height}:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2"
                else:
                    base_scale = f"scale={self.target_width}:-1:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2"
                
                print(f"[DEBUG] 目标尺寸: {self.target_width}x{self.target_height}@{self.fps}fps")
                print(f"[DEBUG] 缩放滤镜: {base_scale}")
                
                # 如果需要显示用户名，添加水印
                if username:
                    username_img = generate_temp_filename(output_name, "_username.png", work_output_dir)
                    if render_username_image(username, username_img, width=300, font_size=28):
                        vf = f"{base_scale},format=yuv420p[out];[out][1:v]overlay=(W-w)/2:10[out]"
                        command = [
                            'ffmpeg',
                            '-i', media_file,
                            '-i', username_img,
                            '-filter_complex', vf,
                            '-map', '0:a?',
                            '-map', '[out]',
                            '-r', str(self.fps),
                            '-y',
                            output_name
                        ]
                    else:
                        command = [
                            'ffmpeg',
                            '-i', media_file,
                            '-vf', base_scale,
                            '-r', str(self.fps),
                            '-map', '0:v',
                            '-map', '0:a?',
                            '-y',
                            output_name
                        ]
                else:
                    command = [
                        'ffmpeg',
                        '-i', media_file,
                        '-vf', base_scale,
                        '-r', str(self.fps),
                        '-map', '0:v',
                        '-map', '0:a?',
                        '-y',
                        output_name
                    ]
                
                # 执行FFmpeg命令
                print(f"[DEBUG] 执行FFmpeg命令:")
                print(" ".join(command))
                run_ffmpeg_command(command)
                
                # 检查输出文件是否生成成功
                if os.path.exists(output_name):
                    file_size = os.path.getsize(output_name)
                    print(f"[DEBUG] FFmpeg输出文件生成成功: {output_name}, 大小: {file_size} bytes")
                else:
                    print(f"[ERROR] FFmpeg输出文件未生成: {output_name}")
                
                # 应用原创性提升处理
                print(f"[DEBUG] 开始应用原创性提升处理: {output_name}")
                processed_file = self.originality_service.process_video(
                    output_name,
                    # 随机起点
                    enable_random_start=self.enable_originality,
                    max_offset=self.random_start_max_offset,
                    max_duration=self.random_start_max_duration,
                    # 噪点
                    enable_noise=self.enable_noise,
                    noise_intensity=self.noise_intensity,
                    # 滤镜
                    filter_preset=self.filter_preset,
                )
                return_video_list.append(processed_file)

        # 标准化所有视频尺寸，确保完全一致
        if len(return_video_list) > 1 and self.enable_video_transition_effect:
            return_video_list = self._normalize_video_sizes(return_video_list)
        
        # 将封面视频插入到最前面
        if cover_video and os.path.exists(cover_video):
            return_video_list.insert(0, cover_video)
            print(f"封面视频已插入到视频列表最前面: {cover_video}")

        self.video_list = return_video_list
        return return_video_list

    def _normalize_video_sizes(self, video_list):
        """标准化视频尺寸和帧率，确保所有视频完全一致"""
        print(f"[DEBUG] 开始标准化视频尺寸，共 {len(video_list)} 个视频")
        normalized_list = []
        for i, video_file in enumerate(video_list):
            print(f"[DEBUG] 标准化第 {i+1}/{len(video_list)} 个视频: {video_file}")
            output_file = generate_temp_filename(video_file, "_norm.mp4", work_output_dir)
            command = [
                'ffmpeg', '-i', video_file,
                '-vf', f"scale={self.target_width}:{self.target_height}:force_original_aspect_ratio=increase,crop={self.target_width}:{self.target_height},setsar=1,fps={self.fps}",
                '-r', str(self.fps),
                '-c:v', 'libx264', '-preset', 'fast',
                '-map', '0:v',
                '-map', '0:a?',
                '-y', output_file
            ]
            print(f"[DEBUG] 标准化视频: {self.target_width}x{self.target_height}@{self.fps}fps")
            print(f"[DEBUG] FFmpeg命令: {' '.join(command)}")
            run_ffmpeg_command(command)
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"[DEBUG] 标准化成功，输出文件: {output_file}, 大小: {file_size} bytes")
                normalized_list.append(output_file)
            else:
                print(f"[ERROR] 标准化失败，保持原文件: {video_file}")
                normalized_list.append(video_file)
        return normalized_list

    def generate_video_with_bg_music(self):
        # 生成视频和音频的代码
        print(f"[DEBUG] ========== 开始生成最终视频 ==========")
        print(f"[DEBUG] 视频列表共 {len(self.video_list)} 个:")
        for i, v in enumerate(self.video_list):
            if os.path.exists(v):
                size = os.path.getsize(v)
                print(f"[DEBUG]   [{i+1}] {v} ({size} bytes)")
            else:
                print(f"[DEBUG]   [{i+1}] {v} (文件不存在!)")
        
        random_name = str(random_with_system_time())
        merge_video = os.path.join(video_output_dir, "final-" + random_name + ".mp4")
        temp_video_filelist_path = os.path.join(video_output_dir, 'generate_video_with_bg_file_list.txt')

        # 创建包含所有视频文件的文本文件
        print(f"[DEBUG] 创建视频文件列表: {temp_video_filelist_path}")
        with open(temp_video_filelist_path, 'w') as f:
            for video_file in self.video_list:
                f.write(f"file '{video_file}'\n")
                print(f"[DEBUG]   添加: {video_file}")

        # 拼接视频
        ffmpeg_concat_cmd = ['ffmpeg',
                             '-f', 'concat',
                             '-safe', '0',
                             '-i', temp_video_filelist_path,
                             '-c', 'copy',
                             '-fflags',
                             '+genpts',
                             '-y',
                             merge_video]

        # 检查是否有音频流（排除封面视频）
        has_audio = False
        videos_with_audio = []
        for video_file in self.video_list:
            # 跳过封面视频
            if 'cover_video' in video_file:
                continue
            try:
                result = subprocess.run(
                    ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_type', 
                     '-of', 'csv=p=0', video_file],
                    capture_output=True, text=True
                )
                if 'audio' in result.stdout.lower():
                    has_audio = True
                    videos_with_audio.append(video_file)
            except:
                pass
        
        print(f"[DEBUG] 音频检查 - has_audio: {has_audio}, videos_with_audio数量: {len(videos_with_audio)}")

        # 如果有封面视频，需要单独处理
        has_cover = any('cover_video' in v for v in self.video_list)

        # 是否需要转场特效
        if self.enable_video_transition_effect and len(self.video_list) > 1:
            # 获取实际有音频的视频时长
            real_videos = [v for v in self.video_list if 'cover_video' not in v]
            if len(real_videos) <= 1:
                print("视频数量不足1个，执行简单拼接")
                with open(temp_video_filelist_path, 'w') as f:
                    for video_file in self.video_list:
                        f.write(f"file '{video_file}'\n")
                ffmpeg_concat_cmd = ['ffmpeg',
                                     '-f', 'concat', '-safe', '0',
                                     '-i', temp_video_filelist_path,
                                     '-c:v', 'libx264', '-preset', 'fast',
                                     '-c:a', 'aac', '-b:a', '128k',
                                     '-r', str(self.fps),
                                     '-y', merge_video]
                print(f"[DEBUG] 简单拼接FFmpeg命令: {' '.join(ffmpeg_concat_cmd)}")
                result = subprocess.run(ffmpeg_concat_cmd, capture_output=True, encoding='utf-8', errors='replace')
                if result.returncode != 0:
                    print(f"[ERROR] 简单拼接FFmpeg失败:")
                    print(result.stderr if result.stderr else "Unknown error")
            else:
                # 多个视频，使用xfade转场
                print("启动转场特效（视频xfade转场）")
                video_length_list = get_video_length_list(real_videos)
                zhuanchang_txt = gen_filter(video_length_list, None, None,
                                            self.video_transition_effect_type,
                                            self.video_transition_effect_value,
                                            self.video_transition_effect_duration,
                                            False)

                files_input = [['-i', f] for f in real_videos]
                
                # 第一步：生成视频xfade（不包含音频）
                ffmpeg_concat_cmd = ['ffmpeg', *itertools.chain(*files_input),
                                     '-filter_complex', zhuanchang_txt,
                                     '-map', '[video]',
                                     '-c:v', 'libx264', '-preset', 'fast',
                                     '-r', str(self.fps),
                                     '-y',
                                     merge_video]
                print(f"[DEBUG] FFmpeg转场命令: {' '.join(ffmpeg_concat_cmd)}")
                result = subprocess.run(ffmpeg_concat_cmd, capture_output=True, encoding='utf-8', errors='replace')
                if result.returncode != 0:
                    print(f"[ERROR] 转场特效FFmpeg失败:")
                    print(result.stderr if result.stderr else "Unknown error")
                else:
                    print("[DEBUG] 转场视频生成成功")
                    
                    # 第二步：拼接音频并混合到视频
                    if has_audio:
                        print("[DEBUG] 开始拼接音频...")
                        audio_list_file = os.path.join(video_output_dir, 'audio_list.txt')
                        with open(audio_list_file, 'w', encoding='utf-8') as f:
                            for v in real_videos:
                                f.write(f"file '{v}'\n")
                        
                        temp_audio = merge_video.replace('.mp4', '_audio.aac')
                        temp_audio_cmd = ['ffmpeg', '-y',
                                         '-f', 'concat', '-safe', '0',
                                         '-i', audio_list_file,
                                         '-c:a', 'copy',
                                         '-vn',
                                         temp_audio]
                        print(f"[DEBUG] 音频拼接命令: {' '.join(temp_audio_cmd)}")
                        result = subprocess.run(temp_audio_cmd, capture_output=True, encoding='utf-8', errors='replace')
                        
                        if result.returncode == 0 and os.path.exists(temp_audio):
                            # 检查合并后音频的时长
                            audio_duration = 0
                            try:
                                probe = subprocess.run(
                                    ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                     '-of', 'default=noprint_wrappers=1:nokey=1', temp_audio],
                                    capture_output=True, text=True
                                )
                                audio_duration = float(probe.stdout.strip())
                            except:
                                pass
                            
                            # 将音频混合到视频
                            temp_video_with_audio = merge_video.replace('.mp4', '_with_audio.mp4')
                            mix_cmd = ['ffmpeg', '-y',
                                      '-i', merge_video,
                                      '-i', temp_audio,
                                      '-c:v', 'copy',
                                      '-c:a', 'aac', '-b:a', '128k',
                                      '-shortest',
                                      temp_video_with_audio]
                            print(f"[DEBUG] 混合音视频命令: {' '.join(mix_cmd)}")
                            result = subprocess.run(mix_cmd, capture_output=True, encoding='utf-8', errors='replace')
                            
                            if result.returncode == 0 and os.path.exists(temp_video_with_audio):
                                os.remove(merge_video)
                                os.rename(temp_video_with_audio, merge_video)
                                print("[DEBUG] 音频拼接成功")
                            else:
                                print(f"[ERROR] 混合音视频失败: {result.stderr if result.stderr else 'Unknown error'}")
                            if os.path.exists(temp_audio):
                                os.remove(temp_audio)
                        else:
                            print(f"[ERROR] 音频拼接失败: {result.stderr if result.stderr else 'Unknown error'}")
                        
                        if os.path.exists(audio_list_file):
                            os.remove(audio_list_file)
            
            # 如果有封面视频，拼接封面到最前面
            if has_cover:
                cover_video = next(v for v in self.video_list if 'cover_video' in v)
                # 先保存合并的视频
                temp_merge = merge_video.replace('.mp4', '_no_cover.mp4')
                if os.path.exists(merge_video) and os.path.getsize(merge_video) > 1000:
                    os.rename(merge_video, temp_merge)
                    
                    # 检查合并后的视频是否有音频
                    temp_has_audio = False
                    try:
                        result = subprocess.run(
                            ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_type', 
                             '-of', 'csv=p=0', temp_merge],
                            capture_output=True, text=True
                        )
                        temp_has_audio = 'audio' in result.stdout.lower()
                    except:
                        pass
                    
                    # 拼接封面 - 强制重新编码以避免时间戳问题
                    concat_file = temp_merge.replace('.mp4', '_concat.txt')
                    with open(concat_file, 'w') as f:
                        f.write(f"file '{cover_video}'\n")
                        f.write(f"file '{temp_merge}'\n")
                    
                    # 强制重新编码而不是copy模式
                    concat_cmd = ['ffmpeg',
                                  '-f', 'concat', '-safe', '0', '-i', concat_file,
                                  '-c:v', 'libx264', '-preset', 'fast',
                                  '-c:a', 'aac', '-b:a', '128k',
                                  '-r', str(self.fps),
                                  '-y', merge_video]
                    print(f"[DEBUG] 封面拼接FFmpeg命令: {' '.join(concat_cmd)}")
                    subprocess.run(concat_cmd, capture_output=True, encoding='utf-8', errors='replace')
                    
                    # 验证最终视频
                    if os.path.exists(merge_video):
                        final_size = os.path.getsize(merge_video)
                        print(f"[DEBUG] 最终视频已生成: {merge_video}, 大小: {final_size} bytes")
                        if final_size < 1000:
                            print(f"[ERROR] 最终视频文件过小，可能生成失败!")
                    else:
                        print(f"[ERROR] 最终视频文件未生成!")
                    
                    # 验证合并后的视频是否有音频
                    final_has_audio = False
                    try:
                        result = subprocess.run(
                            ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_type', 
                             '-of', 'csv=p=0', merge_video],
                            capture_output=True, text=True
                        )
                        final_has_audio = 'audio' in result.stdout.lower()
                        print(f"[DEBUG] 最终视频音频检查 - has_audio: {final_has_audio}")
                    except:
                        pass
                    
                    # 清理临时文件
                    if os.path.exists(temp_merge):
                        os.remove(temp_merge)
                    if os.path.exists(concat_file):
                        os.remove(concat_file)
                else:
                    print(f"警告: 转场特效生成失败，跳过封面拼接")
                    # 删除无效文件
                    if os.path.exists(merge_video):
                        os.remove(merge_video)
            else:
                # 不启用转场特效时，使用简单拼接
                print("不启用转场特效，执行简单视频拼接（强制重新编码）")
                # 重新构建文件列表（包含所有视频）
                with open(temp_video_filelist_path, 'w') as f:
                    for video_file in self.video_list:
                        f.write(f"file '{video_file}'\n")
                # 使用强制重新编码而不是copy模式，避免时间戳问题
                ffmpeg_concat_cmd = ['ffmpeg',
                                     '-f', 'concat',
                                     '-safe', '0',
                                     '-i', temp_video_filelist_path,
                                     '-c:v', 'libx264', '-preset', 'fast',
                                     '-c:a', 'aac', '-b:a', '128k',
                                     '-r', str(self.fps),
                                     '-y',
                                     merge_video]
                print(f"[DEBUG] 简单拼接FFmpeg命令: {' '.join(ffmpeg_concat_cmd)}")
                result = subprocess.run(ffmpeg_concat_cmd, capture_output=True, encoding='utf-8', errors='replace')
                if result.returncode != 0:
                    print(f"[ERROR] 简单拼接FFmpeg失败:")
                    print(result.stderr if result.stderr else "Unknown error")
        else:
            # 不启用转场特效且视频数量 <= 1
            print("视频数量不足或未启用转场，执行简单视频拼接（强制重新编码）")
            # 使用强制重新编码而不是copy模式，避免时间戳问题
            ffmpeg_concat_cmd = ['ffmpeg',
                                 '-f', 'concat',
                                 '-safe', '0',
                                 '-i', temp_video_filelist_path,
                                 '-c:v', 'libx264', '-preset', 'fast',
                                 '-c:a', 'aac', '-b:a', '128k',
                                 '-r', str(self.fps),
                                 '-y',
                                 merge_video]
            print(f"[DEBUG] 简单拼接FFmpeg命令: {' '.join(ffmpeg_concat_cmd)}")
            result = subprocess.run(ffmpeg_concat_cmd, capture_output=True, encoding='utf-8', errors='replace')
            if result.returncode != 0:
                print(f"[ERROR] 简单拼接FFmpeg失败:")
                print(result.stderr if result.stderr else "Unknown error")
        # 删除临时文件
        os.remove(temp_video_filelist_path)

        # 添加背景音乐
        if self.enable_background_music:
            # 如果设置了新BGM目录，随机选择一首音乐
            if self.new_bgm_dir and os.path.isdir(self.new_bgm_dir):
                import glob
                bgm_files = glob.glob(os.path.join(self.new_bgm_dir, "*.mp3")) + \
                           glob.glob(os.path.join(self.new_bgm_dir, "*.wav"))
                if bgm_files:
                    import random
                    selected_bgm = random.choice(bgm_files)
                    print(f"随机选择BGM: {selected_bgm}")
                    self.background_music = selected_bgm
            
            add_background_music(merge_video, self.background_music, self.background_music_volume)
        return merge_video
