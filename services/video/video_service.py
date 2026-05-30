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
import math
import os
import random
import re
import subprocess
import asyncio
from typing import List
import streamlit as st

from PIL import Image

from services.video.texiao_service import gen_filter
from tools.file_utils import generate_temp_filename
from tools.tr_utils import tr
from tools.utils import random_with_system_time, run_ffmpeg_command, extent_audio

# 获取当前脚本的绝对路径
script_path = os.path.abspath(__file__)

# print("当前脚本的绝对路径是:", script_path)

# 脚本所在的目录
script_dir = os.path.dirname(script_path)
# 视频出目录
video_output_dir = os.path.join(script_dir, "../../final")
video_output_dir = os.path.abspath(video_output_dir)

# work目录
work_output_dir = os.path.join(script_dir, "../../work")
work_output_dir = os.path.abspath(work_output_dir)

DEFAULT_DURATION = 5


def get_audio_duration(audio_file):
    """
    获取音频文件的时长（秒）
    :param audio_file: 音频文件路径
    :return: 音频时长（秒），如果失败则返回None
    """
    # 使用ffmpeg命令获取音频信息
    cmd = ['ffmpeg', '-i', audio_file]
    print(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True)

    # 解析输出，找到时长信息
    duration_search = re.search(
        r'Duration: (?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+)\.(?P<milliseconds>\d+)',
        result.stderr.decode('utf-8'))
    if duration_search:
        hours = int(duration_search.group('hours'))
        minutes = int(duration_search.group('minutes'))
        seconds = int(duration_search.group('seconds'))
        total_seconds = hours * 3600 + minutes * 60 + seconds
        print("音频时长:", total_seconds)
        return total_seconds
    else:
        print(f"无法从输出中获取音频时长: {result.stderr.decode('utf-8')}")
        return None


def get_video_fps(video_path):
    # ffprobe 命令，用于获取视频的帧率
    ffprobe_cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    print(" ".join(ffprobe_cmd))

    try:
        # 运行 ffprobe 命令并捕获输出
        result = subprocess.run(ffprobe_cmd, capture_output=True)
        stdout = result.stdout.decode('gbk', errors='ignore')
        stderr = result.stderr.decode('gbk', errors='ignore')

        # 检查命令是否成功执行
        if result.returncode != 0:
            print(f"Error running ffprobe: {result.stderr}")
            return None

        # 解析输出以获取帧率
        output = result.stdout.strip()
        if '/' in output:
            numerator, denominator = map(int, output.split('/'))
            fps = float(numerator) / float(denominator)
        else:
            fps = float(output)
        print("视频fps:", fps)
        return fps
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_video_info(video_file):
    command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of',
               'default=noprint_wrappers=1:nokey=1', video_file]
    print(" ".join(command))
    result = subprocess.run(command, capture_output=True)

    # 解析输出以获取宽度和高度
    output = result.stdout.decode('utf-8')
    # print("output is:",output)
    width_height = output.split('\n')
    width = int(width_height[0])
    height = int(width_height[1])

    print(f'Width: {width}, Height: {height}')
    return width, height


def get_image_info(image_file):
    # 打开图片
    img = Image.open(image_file)
    # 获取图片的宽度和高度
    width, height = img.size
    print(f'Width: {width}, Height: {height}')
    return width, height


def get_video_duration(video_file):
    # 构建FFmpeg命令来获取视频时长
    command = ['ffprobe', '-i', video_file, '-show_entries', 'format=duration']
    # 执行命令并捕获输出
    print(" ".join(command))
    result = subprocess.run(command, capture_output=True)
    output = result.stdout.decode('utf-8')

    # 使用正则表达式从输出中提取时长
    duration_match = re.search(r'duration=(\d+\.\d+)', output)
    if duration_match:
        duration = float(duration_match.group(1))
        print("视频时长:", duration)
        return duration
    else:
        print(f"无法从输出中提取视频时长: {output}")
        return None


def get_video_length_list(video_list):
    video_length_list = []
    for video_file in video_list:
        length = get_video_duration(video_file)
        video_length_list.append(length)
    return video_length_list


def add_music(video_file, audio_file):
    output_file = generate_temp_filename(video_file)
    # 构造ffmpeg命令
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', video_file,  # 输入视频文件
        '-i', audio_file,  # 输入音频文件
        '-c:v', 'copy',  # 复制视频流编码
        '-c:a', 'aac',  # 使用AAC编码音频流
        '-strict', 'experimental',  # 有时可能需要这个选项来启用AAC编码
        '-map', '0:v:0',  # 选择第一个输入文件的视频流
        '-map', '1:a:0',  # 选择第二个输入文件的音频流
        '-shortest',
        '-y',
        output_file  # 输出文件路径
    ]
    print(" ".join(ffmpeg_cmd))
    result = subprocess.run(ffmpeg_cmd, capture_output=True)
    stdout = result.stdout.decode('gbk', errors='ignore')
    stderr = result.stderr.decode('gbk', errors='ignore')
    # 重命名最终的文件
    if os.path.exists(output_file):
        os.remove(video_file)
        os.renames(output_file, video_file)


def add_background_music(video_file, audio_file, bgm_volume=0.5):
    output_file = generate_temp_filename(video_file)
    
    # 先检查视频是否有音频流
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_type',
         '-of', 'csv=p=0', video_file],
        capture_output=True, text=True
    )
    has_audio = 'audio' in result.stdout.lower()
    
    if has_audio:
        # 视频有音频，混合原音频和BGM
        filter_complex = (
            f"[1:a]aloop=loop=0:size=100M[bgm];[bgm]volume={bgm_volume}[bgm_vol];"
            f"[0:a][bgm_vol]amix=duration=first:dropout_transition=3:inputs=2[a]"
        )
        audio_map = '[a]'
    else:
        # 视频没有音频，直接使用BGM
        filter_complex = f"[1:a]aloop=loop=0:size=100M,volume={bgm_volume}[a]"
        audio_map = '[a]'
    
    # 构建FFmpeg命令
    command = [
        'ffmpeg',
        '-i', video_file,  # 输入视频文件
        '-i', audio_file,  # 输入音频文件（背景音乐）
        '-filter_complex', filter_complex,
        '-map', '0:v',  # 选择视频流
        '-map', audio_map,  # 选择混合后的音频流
        '-c:v', 'copy',  # 复制视频流
        '-shortest',  # 输出时长与最短的输入流相同
        output_file  # 输出文件
    ]
    # 调用FFmpeg命令
    print(command)
    result = subprocess.run(command, capture_output=True)
    # 处理输出解码
    stdout = result.stdout.decode('gbk', errors='ignore')
    stderr = result.stderr.decode('gbk', errors='ignore')
    # 重命名最终的文件
    if os.path.exists(output_file):
        os.remove(video_file)
        os.renames(output_file, video_file)


def extract_video_frame(video_file, timestamp, output_image):
    """从视频中截取指定时间点的帧作为图片"""
    command = [
        'ffmpeg', '-ss', str(timestamp),
        '-i', video_file,
        '-vframes', '1',
        '-y', output_image
    ]
    print(f"截取封面帧: {video_file} @ {timestamp}s")
    result = subprocess.run(command, capture_output=True)
    return os.path.exists(output_image)


def create_4grid_cover(frame_files, output_image, thumb_width, thumb_height, line1=None, line2=None):
    """创建4宫格封面图，带文字"""
    if len(frame_files) < 4:
        print(f"帧文件数量不足: {len(frame_files)}")
        return False

    w, h = thumb_width, thumb_height

    # 先缩放每个帧到统一尺寸并保存
    scaled_files = []
    for i, frame in enumerate(frame_files[:4]):
        scaled = os.path.join(os.path.dirname(output_image), f'scaled_{i}.jpg')
        scale_cmd = [
            'ffmpeg', '-i', frame,
            '-vf', f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}',
            '-y', scaled
        ]
        subprocess.run(scale_cmd, capture_output=True)
        if os.path.exists(scaled):
            scaled_files.append(scaled)

    if len(scaled_files) < 4:
        print(f"缩放失败，只成功 {len(scaled_files)} 个")
        return False

    # 使用ffmpeg的vstack和hstack拼接
    # 先横向拼接每行
    top_row = os.path.join(os.path.dirname(output_image), 'top_row.jpg')
    bottom_row = os.path.join(os.path.dirname(output_image), 'bottom_row.jpg')

    hstack1 = subprocess.run([
        'ffmpeg', '-i', scaled_files[0], '-i', scaled_files[1],
        '-filter_complex', 'hstack=inputs=2', '-y', top_row
    ], capture_output=True)

    hstack2 = subprocess.run([
        'ffmpeg', '-i', scaled_files[2], '-i', scaled_files[3],
        '-filter_complex', 'hstack=inputs=2', '-y', bottom_row
    ], capture_output=True)

    # 再纵向拼接
    vstack = subprocess.run([
        'ffmpeg', '-i', top_row, '-i', bottom_row,
        '-filter_complex', 'vstack=inputs=2', '-y', output_image
    ], capture_output=True)

    # 清理临时文件
    for f in scaled_files + [top_row, bottom_row]:
        if os.path.exists(f):
            os.remove(f)

    if os.path.exists(output_image):
        # 在封面上添加文字
        add_text_to_cover(output_image, output_image, line1, line2)

    success = os.path.exists(output_image)
    print(f"4宫格封面创建{'成功' if success else '失败'}")
    return success


def add_text_to_cover(input_image, output_image, line1=None, line2=None):
    """在封面上添加粉色文字"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import streamlit as st

        img = Image.open(input_image)
        draw = ImageDraw.Draw(img)

        # 获取用户输入的文字（默认）
        if line1 is None:
            line1 = st.session_state.get("sequential_cover_line1", "盘点漂亮小美女")
        if line2 is None:
            line2 = st.session_state.get("sequential_cover_line2", "你最喜欢哪一位")

        # 如果文字为空，不添加
        if not line1 and not line2:
            img.save(output_image)
            return True

        # 获取字体，增大到96
        font_size = 96
        font = None
        for fp in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/simsun.ttc']:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, font_size)
                break
        if font is None:
            font = ImageFont.load_default()

        # 粉色颜色 (偏暖的粉红色)
        pink_color = (255, 105, 180)  # HotPink
        shadow_color = (139, 0, 70)   # 深粉红作为阴影

        img_width, img_height = img.size

        # 如果只有一行文字
        if line1 and not line2:
            bbox1 = draw.textbbox((0, 0), line1, font=font)
            text1_width = bbox1[2] - bbox1[0]
            text1_height = bbox1[3] - bbox1[1]
            x1 = (img_width - text1_width) // 2
            y1 = (img_height - text1_height) // 2
            stroke_width = 4
            draw.text((x1, y1), line1, font=font, fill=shadow_color, stroke_width=stroke_width, stroke_fill=shadow_color)
            draw.text((x1, y1), line1, font=font, fill=pink_color)
        elif line1 and line2:
            # 两行文字
            bbox1 = draw.textbbox((0, 0), line1, font=font)
            bbox2 = draw.textbbox((0, 0), line2, font=font)

            text1_width = bbox1[2] - bbox1[0]
            text1_height = bbox1[3] - bbox1[1]
            text2_width = bbox2[2] - bbox2[0]
            text2_height = bbox2[3] - bbox2[1]

            line_spacing = 15
            total_text_height = text1_height + line_spacing + text2_height

            # 第一行位置（垂直居中偏上）
            y1 = (img_height - total_text_height) // 2 - 20
            # 第二行位置
            y2 = y1 + text1_height + line_spacing

            # 第一行 x 居中
            x1 = (img_width - text1_width) // 2
            # 第二行 x 居中
            x2 = (img_width - text2_width) // 2

            stroke_width = 4
            # 绘制阴影
            draw.text((x1, y1), line1, font=font, fill=shadow_color, stroke_width=stroke_width, stroke_fill=shadow_color)
            draw.text((x2, y2), line2, font=font, fill=shadow_color, stroke_width=stroke_width, stroke_fill=shadow_color)

            # 绘制主文字
            draw.text((x1, y1), line1, font=font, fill=pink_color)
            draw.text((x2, y2), line2, font=font, fill=pink_color)

        img.save(output_image)
        print("封面文字添加成功")
        return True
    except Exception as e:
        print(f"添加封面文字失败: {e}")
        return False


async def _generate_cover_tts_async(text, output_audio):
    """异步生成封面语音"""
    try:
        import edge_tts
        # 使用 XiaoyiNeural - 标准中文女声，发音准确
        voice = "zh-CN-XiaoyiNeural"
        communicate = edge_tts.Communicate(text, voice=voice, rate="+0%", pitch="+0Hz")
        await communicate.save(output_audio)
        print(f"[封面语音] 使用声音: {voice}")
        return True
    except Exception as e:
        print(f"生成封面语音失败: {e}")
        # 备用声音 XiaoxiaoNeural
        try:
            import edge_tts
            voice = "zh-CN-XiaoxiaoNeural"
            communicate = edge_tts.Communicate(text, voice=voice, rate="+0%", pitch="+0Hz")
            await communicate.save(output_audio)
            print(f"[封面语音] 备用声音: {voice}")
            return True
        except Exception as e2:
            print(f"备用声音也失败: {e2}")
            return False


def generate_cover_tts(line1, line2, output_audio):
    """生成封面文字的语音（温柔女生声音）"""
    # 组合两行文字
    if line1 and line2:
        text = f"{line1}，{line2}"
    elif line1:
        text = line1
    elif line2:
        text = line2
    else:
        return None

    print(f"[封面语音] 生成语音: {text}")
    try:
        asyncio.run(_generate_cover_tts_async(text, output_audio))
        if os.path.exists(output_audio):
            print(f"[封面语音] 已生成: {output_audio}")
            return output_audio
    except Exception as e:
        print(f"[封面语音] 生成失败: {e}")
    return None


def get_audio_duration(audio_file):
    """获取音频文件时长（秒）"""
    try:
        # 使用 ffprobe 获取音频时长
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', audio_file
        ], capture_output=True, text=True, encoding='utf-8')
        duration = float(result.stdout.strip())
        print(f"[音频时长] {audio_file}: {duration}秒")
        return duration
    except Exception as e:
        print(f"获取音频时长失败: {e}")
        return 3.0  # 默认3秒


def create_cover_video_with_audio(image_file, duration, fps, width, height, output_video, audio_file=None):
    """将图片转换为视频，可选添加音频"""
    if audio_file and os.path.exists(audio_file):
        # 获取音频时长
        audio_duration = get_audio_duration(audio_file)
        video_duration = max(duration, audio_duration)

        # 使用音频作为音频源，视频时长与音频对齐
        command = [
            'ffmpeg',
            '-loop', '1', '-i', image_file,
            '-i', audio_file,
            '-t', str(video_duration),
            '-r', str(fps),
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}',
            '-c:v', 'libx264', '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-ar', '44100', '-ac', '2',
            '-shortest',
            '-y', output_video
        ]
    else:
        # 无音频，使用静音
        command = [
            'ffmpeg',
            '-loop', '1', '-i', image_file,
            '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=stereo',
            '-t', str(duration),
            '-r', str(fps),
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}',
            '-c:v', 'libx264', '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-ar', '44100', '-ac', '2',
            '-shortest',
            '-y', output_video
        ]

    print(f"封面图转视频: {image_file} -> {output_video}")
    subprocess.run(command, capture_output=True)
    return os.path.exists(output_video)


def create_cover_video(image_file, duration, fps, width, height, output_video):
    """将图片转换为视频（带静音音频流）"""
    return create_cover_video_with_audio(image_file, duration, fps, width, height, output_video, None)
    """将图片转换为视频（带静音音频流）"""
    # 使用 anullsrc 创建静音音频流，确保拼接时音频流不会被丢弃
    command = [
        'ffmpeg',
        '-loop', '1', '-i', image_file,
        '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=stereo',
        '-t', str(duration),
        '-r', str(fps),
        '-vf', f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}',
        '-c:v', 'libx264', '-preset', 'fast',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-ar', '44100', '-ac', '2',
        '-shortest',
        '-y', output_video
    ]
    print(f"封面图转视频: {image_file} -> {output_video}")
    subprocess.run(command, capture_output=True)
    return os.path.exists(output_video)


def generate_video_cover(video_list, output_dir, video_width, video_height, fps, timestamp=2, line1=None, line2=None):
    """
    生成4宫格封面视频（每个格子播放各自的视频片段）

    Args:
        video_list: 视频文件列表（需要>=4个）
        output_dir: 输出目录
        video_width: 视频宽度
        video_height: 视频高度
        fps: 帧率
        timestamp: 截取帧的时间点（秒）
        line1: 封面第一行文字
        line2: 封面第二行文字

    Returns:
        (cover_image_path, cover_video_path) or (None, None) if failed
    """
    import uuid
    from tools.file_utils import generate_temp_filename

    print(f"[DEBUG] generate_video_cover 被调用，视频列表: {video_list[:2]}...")

    if len(video_list) < 4:
        print(f"视频数量不足4个，无法生成4宫格封面。当前有 {len(video_list)} 个视频")
        return None, None

    # 缩略图尺寸（视频尺寸的一半）
    thumb_width = video_width // 2
    thumb_height = video_height // 2

    # 生成封面语音，获取语音时长作为视频总时长
    cover_audio = None
    audio_duration = 4  # 默认4秒
    if line1 or line2:
        cover_audio_file = os.path.join(output_dir, 'cover_audio.mp3')
        cover_audio = generate_cover_tts(line1, line2, cover_audio_file)
        if cover_audio and os.path.exists(cover_audio):
            audio_duration = get_audio_duration(cover_audio)
            if not audio_duration or audio_duration < 1:
                audio_duration = 4
    print(f"[DEBUG] 封面语音时长: {audio_duration}秒")

    # 创建临时目录
    tmp_dir = os.path.join(output_dir, 'cover_tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    # 创建带文字的覆盖层（用于叠加在视频上）
    text_overlay_path = os.path.join(tmp_dir, 'text_overlay.png')
    create_cover_text_overlay(video_width, video_height, line1, line2, text_overlay_path)

    # 缩放4个视频到格子尺寸，并截取指定时长
    scaled_videos = []
    for i, video_file in enumerate(video_list[:4]):
        scaled_video = os.path.join(tmp_dir, f'cover_scaled_{i}.mp4')

        # 缩放视频到格子尺寸，并截取封面语音时长的片段
        vf = f'scale={thumb_width}:{thumb_height}:force_original_aspect_ratio=increase,crop={thumb_width}:{thumb_height}'

        command = [
            'ffmpeg', '-y',
            '-i', video_file,
            '-vf', vf,
            '-t', str(audio_duration),
            '-r', str(fps),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-an',  # 移除音频
            '-pix_fmt', 'yuv420p',
            scaled_video
        ]

        print(f"[DEBUG] 缩放第 {i+1} 个视频...")
        result = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace')
        if result.returncode != 0 or not os.path.exists(scaled_video):
            print(f"[DEBUG] 缩放第 {i+1} 个视频失败")
            # 清理并返回失败
            import shutil
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            return None, None
        scaled_videos.append(scaled_video)

    # 创建4宫格视频（先不加文字）
    cover_video_raw = os.path.join(tmp_dir, 'cover_raw.mp4')

    # 使用 filter_complex 创建4宫格
    filter_complex = f"""
    [1:v][2:v]hstack=inputs=2[top];
    [3:v][4:v]hstack=inputs=2[bottom];
    [top][bottom]vstack=inputs=2[grid]
    """

    command = [
        'ffmpeg', '-y',
        '-i', scaled_videos[0],  # 占位符（会被 grid 替换）
        '-i', scaled_videos[0],
        '-i', scaled_videos[1],
        '-i', scaled_videos[2],
        '-i', scaled_videos[3],
        '-filter_complex', filter_complex,
        '-map', '[grid]',
        '-t', str(audio_duration),
        '-r', str(fps),
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-pix_fmt', 'yuv420p',
        cover_video_raw
    ]

    print(f"[DEBUG] 创建4宫格视频...")
    result = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        print(f"[DEBUG] 创建4宫格失败: {result.stderr[:300] if result.stderr else '未知错误'}")
        import shutil
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        return None, None

    # 添加文字 overlay
    cover_video_no_audio = os.path.join(tmp_dir, 'cover_with_text.mp4')
    cover_video = os.path.join(output_dir, 'cover_video.mp4')
    
    if os.path.exists(text_overlay_path):
        # 使用 overlay 叠加文字
        cmd = [
            'ffmpeg', '-y',
            '-i', cover_video_raw,
            '-i', text_overlay_path,
            '-filter_complex', '[0:v][1:v]overlay=0:0[out]',
            '-map', '[out]',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-pix_fmt', 'yuv420p',
            cover_video_no_audio
        ]
        print(f"[DEBUG] 添加文字 overlay...")
        result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"[DEBUG] 添加文字失败: {result.stderr[:200] if result.stderr else '未知错误'}")
            import shutil
            shutil.copy(cover_video_raw, cover_video_no_audio)
    else:
        import shutil
        shutil.copy(cover_video_raw, cover_video_no_audio)

    # 添加封面语音
    if cover_audio and os.path.exists(cover_audio):
        cmd = [
            'ffmpeg', '-y',
            '-i', cover_video_no_audio,
            '-i', cover_audio,
            '-c:v', 'copy',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest',
            cover_video
        ]
        result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"[DEBUG] 添加封面语音失败: {result.stderr[:200] if result.stderr else '未知错误'}")
            import shutil
            shutil.copy(cover_video_no_audio, cover_video)
    else:
        import shutil
        shutil.copy(cover_video_no_audio, cover_video)

    # 生成封面图片（用于预览）
    cover_image = os.path.join(output_dir, 'cover.jpg')
    temp_frame = os.path.join(tmp_dir, 'temp_frame.jpg')
    if extract_video_frame(cover_video, 0.5, temp_frame):
        from PIL import Image
        img = Image.open(temp_frame)
        img.save(cover_image)
        if os.path.exists(temp_frame):
            os.remove(temp_frame)
        print(f"[DEBUG] 封面图片已保存: {cover_image}")

    # 清理临时目录
    try:
        import shutil
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
    except:
        pass

    print(f"[DEBUG] 4宫格封面视频已创建: {cover_video}")
    return cover_image, cover_video


def create_cover_background_with_text(width, height, line1, line2, output_path):
    """创建带文字的封面背景图"""
    from PIL import Image, ImageDraw, ImageFont

    # 创建黑色背景
    img = Image.new('RGB', (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    if not line1 and not line2:
        img.save(output_path)
        return

    # 字体大小
    font_size = height // 15
    font = None
    for fp in ['C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simsun.ttc']:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except:
                pass
    if font is None:
        font = ImageFont.load_default()

    # 粉色文字
    text_color = (255, 105, 180)  # HotPink
    shadow_color = (0, 0, 0)

    # 文字位置：底部居中
    texts = []
    if line1:
        texts.append(line1)
    if line2:
        texts.append(line2)

    if texts:
        # 计算文字区域高度
        line_height = font_size * 1.5
        total_text_height = len(texts) * line_height
        start_y = height - total_text_height - height // 20

        for i, text in enumerate(texts):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = (width - text_w) // 2
            y = start_y + i * line_height

            # 绘制阴影
            draw.text((x + 3, y + 3), text, font=font, fill=shadow_color)
            # 绘制文字
            draw.text((x, y), text, font=font, fill=text_color)

    img.save(output_path)
    print(f"[DEBUG] 已创建带文字背景: {output_path}")


def create_cover_text_overlay(width, height, line1, line2, output_path):
    """创建文字覆盖层（透明背景，只有文字，用于叠加在视频上）"""
    from PIL import Image, ImageDraw, ImageFont

    # 创建透明背景
    img = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if not line1 and not line2:
        img.save(output_path)
        return

    # 字体大小
    font_size = height // 15
    font = None
    for fp in ['C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simsun.ttc']:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except:
                pass
    if font is None:
        font = ImageFont.load_default()

    # 粉色文字
    text_color = (255, 105, 180, 255)  # HotPink with alpha
    shadow_color = (0, 0, 0, 200)

    # 文字位置：底部居中
    texts = []
    if line1:
        texts.append(line1)
    if line2:
        texts.append(line2)

    if texts:
        # 计算文字区域高度
        line_height = font_size * 1.5
        total_text_height = len(texts) * line_height
        # 文字垂直居中：放在整个视频的中间位置
        text_start_y = (height - total_text_height) // 2

        for i, text in enumerate(texts):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = (width - text_w) // 2
            y = text_start_y + i * line_height

            # 绘制阴影
            draw.text((x + 3, y + 3), text, font=font, fill=shadow_color)
            # 绘制文字
            draw.text((x, y), text, font=font, fill=text_color)

    img.save(output_path)
    print(f"[DEBUG] 已创建文字覆盖层: {output_path}")


def add_text_to_video(input_video, output_video, line1=None, line2=None):
    """在视频上添加文字水印（已废弃，使用 generate_video_cover 中的背景文字方式）"""
    import shutil
    shutil.copy(input_video, output_video)
    return output_video


def add_text_and_audio_to_video(input_video, audio_file, line1=None, line2=None, output_video=None):
    """在视频上添加文字和音频（已废弃，使用 generate_video_cover 中的背景文字方式）"""
    if output_video is None:
        output_video = input_video.replace('.mp4', '_with_audio.mp4')

    command = [
        'ffmpeg', '-y',
        '-i', input_video,
        '-i', audio_file,
        '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest',
        output_video
    ]

    result = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        print(f"[DEBUG] 添加音频失败: {result.stderr[:200]}")
        return None

    return output_video


def add_text_using_pil(input_video, output_video, line1=None, line2=None):
    """使用 PIL 添加文字（已废弃，使用 generate_video_cover 中的背景文字方式）"""
    import shutil
    shutil.copy(input_video, output_video)
    return output_video


def add_text_and_audio_to_video(input_video, audio_file, line1=None, line2=None, output_video=None):
    """在视频上添加文字和音频"""
    if output_video is None:
        output_video = input_video.replace('.mp4', '_with_audio.mp4')

    # 先添加文字（使用 PIL）
    tmp_video = input_video.replace('.mp4', '_with_text.mp4')
    add_text_using_pil(input_video, tmp_video, line1, line2)

    if not os.path.exists(tmp_video):
        print(f"[DEBUG] 添加文字失败，无法继续")
        return None

    # 再添加音频
    command = [
        'ffmpeg', '-y',
        '-i', tmp_video,
        '-i', audio_file,
        '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest',
        output_video
    ]

    print(f"[DEBUG] 添加音频: {audio_file}")
    result = subprocess.run(command, capture_output=True, encoding='utf-8', errors='replace')

    # 清理临时文件
    if os.path.exists(tmp_video):
        try:
            os.remove(tmp_video)
        except:
            pass

    if result.returncode != 0:
        print(f"[DEBUG] 添加音频失败: {result.stderr[:200]}")
        return None

    return output_video


class VideoMixService:
    def __init__(self):
        self.fps = st.session_state["video_fps"]
        self.segment_min_length = st.session_state["video_segment_min_length"]
        self.segment_max_length = st.session_state["video_segment_max_length"]
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
        if DEFAULT_DURATION < self.segment_min_length:
            self.default_duration = self.segment_min_length

    def match_videos_from_dir(self, video_dir, audio_file, is_head=False):
        matching_videos = []
        # 获取音频时长
        audio_duration = get_audio_duration(audio_file)
        print("音频时长:" + str(audio_duration))

        # 获取媒体文件夹中的所有图片和视频文件
        media_files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if
                       f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov'))]

        # 随机排序媒体文件
        random.shuffle(media_files)

        # 确保有视频文件在列表中
        video_files = [os.path.join(video_dir, f) for f in media_files if f.lower().endswith(('.mp4', '.mov'))]
        if video_files:
            # 从视频文件中随机选择一个
            random_video = random.choice(video_files)
            # 将随机选择的视频文件从列表中移除
            media_files.remove(random_video)
            # 将随机选择的视频文件添加到列表的开头
            media_files.insert(0, random_video)

        total_length = 0
        i = 0
        for video_file in media_files:
            if video_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                video_duration = self.default_duration
            else:
                video_duration = get_video_duration(video_file)
            # 短的视频拉长到最小值
            if video_duration < self.segment_min_length:
                video_duration = self.segment_min_length
            if video_duration > self.segment_max_length:
                video_duration = self.segment_max_length

            print("total length:", total_length, "audio length:", audio_duration)
            if total_length < audio_duration:
                if self.enable_video_transition_effect:
                    if i == 0 and is_head:
                        total_length = total_length + video_duration
                    else:
                        total_length = total_length + video_duration - float(
                            self.video_transition_effect_duration)
                else:
                    total_length = total_length + video_duration
                matching_videos.append(video_file)
                i = i + 1
            else:
                extend_length = audio_duration - total_length
                extend_length = int(math.ceil(extend_length))
                if extend_length > 0:
                    extent_audio(audio_file, extend_length)
                break
        print("total length:", total_length, "audio length:", audio_duration)
        if total_length < audio_duration:
            st.toast(tr("You Need More Resource"), icon="⚠️")
            st.stop()
        return matching_videos, total_length


class VideoService:
    def __init__(self, video_list, audio_file):
        self.video_list = video_list
        self.audio_file = audio_file
        self.fps = st.session_state["video_fps"]
        self.seg_min_duration = st.session_state["video_segment_min_length"]
        self.seg_max_duration = st.session_state["video_segment_max_length"]
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
        if DEFAULT_DURATION < self.seg_min_duration:
            self.default_duration = self.seg_min_duration

    def normalize_video(self):
        return_video_list = []
        for media_file in self.video_list:
            # 如果当前文件是图片，添加转换为视频的命令
            if media_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                output_name = generate_temp_filename(media_file, ".mp4", work_output_dir)
                # 判断图片的纵横比和
                img_width, img_height = get_image_info(media_file)
                if img_width / img_height > self.target_width / self.target_height:
                    # 转换图片为视频片段 图片的视频帧率必须要跟视频的帧率一样，否则可能在最后的合并过程中导致 合并过后的视频过长
                    # ffmpeg_cmd = f"ffmpeg -loop 1 -i '{media_file}' -c:v h264 -t {self.default_duration} -r {self.fps} -vf 'scale=-1:{self.target_height}:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2' -y {output_name}"
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-loop', '1',
                        '-i', media_file,
                        '-c:v', 'h264',
                        '-t', str(self.default_duration),
                        '-r', str(self.fps),
                        '-vf',
                        f'scale=-1:{self.target_height}:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2',
                        '-y', output_name]
                else:
                    # ffmpeg_cmd = f"ffmpeg -loop 1 -i '{media_file}' -c:v h264 -t {self.default_duration} -r {self.fps} -vf 'scale={self.target_width}:-1:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2' -y {output_name}"
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-loop', '1',
                        '-i', media_file,
                        '-c:v', 'h264',
                        '-t', str(self.default_duration),
                        '-r', str(self.fps),
                        '-vf',
                        f'scale={self.target_width}:-1:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2',
                        '-y', output_name]
                print(" ".join(ffmpeg_cmd))
                subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
                return_video_list.append(output_name)

            else:
                # 当前文件是视频文件
                video_duration = get_video_duration(media_file)
                video_width, video_height = get_video_info(media_file)
                output_name = generate_temp_filename(media_file, new_directory=work_output_dir)
                if self.seg_min_duration > video_duration:
                    # 需要扩展视频
                    stretch_factor = float(self.seg_min_duration) / float(video_duration)  # 拉长比例
                    # 构建FFmpeg命令
                    if video_width / video_height > self.target_width / self.target_height:
                        command = [
                            'ffmpeg',
                            '-i', media_file,  # 输入文件
                            '-r', str(self.fps),  # 设置帧率
                            '-an',  # 去除音频
                            '-vf',
                            f"setpts={stretch_factor}*PTS,scale=-1:{self.target_height}:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2",
                            # 调整时间戳滤镜
                            # '-vf', f'scale=-1:{self.target_height}:force_original_aspect_ratio=1',  # 设置视频滤镜来调整分辨率
                            # '-vf', f'crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2',
                            # '-af', f'atempo={1 / stretch_factor}',  # 调整音频速度以匹配视频
                            '-y',
                            output_name  # 输出文件
                        ]
                    else:
                        command = [
                            'ffmpeg',
                            '-i', media_file,  # 输入文件
                            '-r', str(self.fps),  # 设置帧率
                            '-an',  # 去除音频
                            '-vf',
                            f"setpts={stretch_factor}*PTS,scale={self.target_width}:-1:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2",
                            # 调整时间戳滤镜
                            # '-vf', f'scale={self.target_width}:-1:force_original_aspect_ratio=1',  # 设置视频滤镜来调整分辨率
                            # '-vf', f'crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2',
                            # '-af', f'atempo={1 / stretch_factor}',  # 调整音频速度以匹配视频
                            '-y',
                            output_name  # 输出文件
                        ]
                    # 执行FFmpeg命令
                    print(" ".join(command))
                    run_ffmpeg_command(command)
                elif self.seg_max_duration < video_duration:
                    # 需要裁减视频
                    if video_width / video_height > self.target_width / self.target_height:
                        cmd = [
                            'ffmpeg',
                            '-i', media_file,
                            '-r', str(self.fps),  # 设置帧率
                            '-an',  # 去除音频
                            # '-ss', '00:00:00',
                            '-t', str(self.seg_max_duration),
                            # '-c', 'copy',
                            # '-vcodec', 'copy',
                            # '-acodec', 'copy',
                            '-vf',
                            f"scale=-1:{self.target_height}:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2",
                            # 设置视频滤镜来调整分辨率
                            # '-vf', f'crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2',
                            '-y',
                            output_name
                        ]
                    else:
                        cmd = [
                            'ffmpeg',
                            '-i', media_file,
                            '-r', str(self.fps),  # 设置帧率
                            '-an',  # 去除音频
                            # '-ss', '00:00:00',
                            '-t', str(self.seg_max_duration),
                            # '-c', 'copy',
                            # '-vcodec', 'copy',
                            # '-acodec', 'copy',
                            '-vf',
                            f"scale={self.target_width}:-1:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2",
                            # 设置视频滤镜来调整分辨率
                            # '-vf', f'crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2',
                            '-y',
                            output_name
                        ]
                    print(" ".join(cmd))
                    run_ffmpeg_command(cmd)
                else:
                    # 不需要拉伸也不需要裁剪，只需要调整分辨率和fps
                    if video_width / video_height > self.target_width / self.target_height:
                        command = [
                            'ffmpeg',
                            '-i', media_file,  # 输入文件
                            '-r', str(self.fps),  # 设置帧率
                            '-an',  # 去除音频
                            '-vf',
                            f"scale=-1:{self.target_height}:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2",
                            # 设置视频滤镜来调整分辨率
                            # '-vf', f'crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2',
                            '-y',
                            output_name  # 输出文件
                        ]
                    else:
                        command = [
                            'ffmpeg',
                            '-i', media_file,  # 输入文件
                            '-r', str(self.fps),  # 设置帧率
                            '-an',  # 去除音频
                            '-vf',
                            f"scale={self.target_width}:-1:force_original_aspect_ratio=1,crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2",
                            # 设置视频滤镜来调整分辨率
                            # '-vf', f'crop={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2',
                            '-y',
                            output_name  # 输出文件
                        ]
                    # 执行FFmpeg命令
                    print(" ".join(command))
                    run_ffmpeg_command(command)
                # 重命名最终的文件
                # if os.path.exists(output_name):
                #     os.remove(media_file)
                #     os.renames(output_name, media_file)
                return_video_list.append(output_name)
        self.video_list = return_video_list
        return return_video_list

    def generate_video_with_audio(self):
        # 生成视频和音频的代码
        random_name = str(random_with_system_time())
        merge_video = os.path.join(video_output_dir, "final-" + random_name + ".mp4")
        temp_video_filelist_path = os.path.join(video_output_dir, 'generate_video_with_audio_file_list.txt')

        # 创建包含所有视频文件的文本文件
        with open(temp_video_filelist_path, 'w') as f:
            for video_file in self.video_list:
                f.write(f"file '{video_file}'\n")

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

        # 是否需要转场特效
        if self.enable_video_transition_effect and len(self.video_list) > 1:
            video_length_list = get_video_length_list(self.video_list)
            print("启动转场特效")
            zhuanchang_txt = gen_filter(video_length_list, None, None,
                                        self.video_transition_effect_type,
                                        self.video_transition_effect_value,
                                        self.video_transition_effect_duration,
                                        False)

            # File inputs from the list
            files_input = [['-i', f] for f in self.video_list]
            ffmpeg_concat_cmd = ['ffmpeg', *itertools.chain(*files_input),
                                 '-filter_complex', zhuanchang_txt,
                                 '-map', '[video]',
                                 # '-map', '[audio]',
                                 '-y',
                                 merge_video]

        subprocess.run(ffmpeg_concat_cmd)
        # 删除临时文件
        os.remove(temp_video_filelist_path)

        # 拼接音频
        add_music(merge_video, self.audio_file)

        # 添加背景音乐
        if self.enable_background_music:
            add_background_music(merge_video, self.background_music, self.background_music_volume)
        return merge_video


def create_black_background_with_text(width, height, text, output_image):
    """创建黑色背景并在中间添加白色文字的图片"""
    try:
        from PIL import Image, ImageDraw, ImageFont

        # 创建黑色背景
        img = Image.new('RGB', (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 获取字体，增大到120
        font_size = 120
        font = None
        for fp in ['C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/simsun.ttc']:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, font_size)
                break
        if font is None:
            font = ImageFont.load_default()

        # 白色文字
        white_color = (255, 255, 255)

        # 计算文字位置（居中）
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        # 绘制文字
        draw.text((x, y), text, font=font, fill=white_color)

        # 保存图片
        img.save(output_image)
        print(f"黑色背景文字图已创建: {output_image}")
        return True
    except Exception as e:
        print(f"创建黑色背景文字图失败: {e}")
        return False


def create_sequential_intro_video(index, width, height, fps, output_video, output_dir):
    """创建顺序介绍镜头视频（黑色背景 + 白色文字 + TTS语音）

    Args:
        index: 当前是第几位（从1开始）
        width: 视频宽度
        height: 视频高度
        fps: 帧率
        output_video: 输出视频路径
        output_dir: 输出目录

    Returns:
        视频文件路径，失败返回None
    """
    # 生成文字
    text = f"第{index}位"

    # 创建黑色背景图片
    temp_image = os.path.join(output_dir, f'intro_{index}_temp.jpg')
    if not create_black_background_with_text(width, height, text, temp_image):
        return None

    # 生成TTS语音
    audio_file = os.path.join(output_dir, f'intro_{index}_audio.mp3')
    tts_audio = generate_intro_tts(text, audio_file)
    if not tts_audio:
        # 如果TTS失败，使用静音
        audio_file = None

    # 获取音频时长
    if audio_file and os.path.exists(audio_file):
        duration = get_audio_duration(audio_file)
    else:
        duration = 2  # 默认2秒

    # 创建视频
    if create_cover_video_with_audio(temp_image, duration, fps, width, height, output_video, audio_file):
        print(f"顺序介绍镜头已创建: {output_video}")
        # 清理临时文件
        if os.path.exists(temp_image):
            os.remove(temp_image)
        return output_video
    else:
        print(f"创建顺序介绍镜头失败: {output_video}")
        return None


async def _generate_intro_tts_async(text, output_audio):
    """异步生成介绍镜头语音"""
    try:
        import edge_tts
        # 使用 XiaoyiNeural - 标准中文女声
        voice = "zh-CN-XiaoyiNeural"
        communicate = edge_tts.Communicate(text, voice=voice, rate="+0%", pitch="+0Hz")
        await communicate.save(output_audio)
        print(f"[介绍镜头语音] 使用声音: {voice}, 文字: {text}")
        return True
    except Exception as e:
        print(f"生成介绍镜头语音失败: {e}")
        return False


def generate_intro_tts(text, output_audio):
    """生成介绍镜头的TTS语音"""
    print(f"[介绍镜头语音] 生成语音: {text}")
    try:
        asyncio.run(_generate_intro_tts_async(text, output_audio))
        if os.path.exists(output_audio):
            print(f"[介绍镜头语音] 已生成: {output_audio}")
            return output_audio
    except Exception as e:
        print(f"[介绍镜头语音] 生成失败: {e}")
    return None
