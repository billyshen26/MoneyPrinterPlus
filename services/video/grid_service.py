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
import random
import subprocess

import streamlit as st

from tools.file_utils import generate_temp_filename
from tools.utils import random_with_system_time

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


def extract_audio_from_video(video_file, output_audio=None):
    """从视频中提取音频"""
    if output_audio is None:
        output_audio = generate_temp_filename(video_file, ".mp3", work_output_dir)

    command = [
        'ffmpeg',
        '-i', video_file,
        '-vn',
        '-acodec', 'mp3',
        '-y',
        output_audio
    ]
    print("提取音频:", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        print(f"提取音频失败: {result.stderr}")
    return output_audio if os.path.exists(output_audio) and os.path.getsize(output_audio) > 0 else None


def get_video_duration(video_file):
    """获取视频时长（秒）"""
    import re
    command = ['ffprobe', '-i', video_file, '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=p=0']
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    try:
        duration = float(result.stdout.strip())
        return duration
    except:
        return None


def get_video_resolution(video_file):
    """获取视频分辨率"""
    command = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=s=x:p=0',
        video_file
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    output = result.stdout.strip()
    if output:
        parts = output.split('x')
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    return None, None


class VideoGridService:
    def __init__(self, video_list, layout='4grid', background_music=None, bgm_volume=0.3):
        self.video_list = video_list
        self.layout = layout
        self.background_music = background_music
        self.bgm_volume = bgm_volume

        self.fps = st.session_state.get("video_fps", 30)

        if self.layout == '4grid':
            self.rows = 2
            self.cols = 2
            self.required_count = 4
        else:
            self.rows = 3
            self.cols = 3
            self.required_count = 9

    def generate_grid_video(self):
        """生成宫格视频"""
        if len(self.video_list) < self.required_count:
            print(f"视频数量不足，需要 {self.required_count} 个视频，当前只有 {len(self.video_list)} 个")
            return None

        selected_videos = self.video_list[:self.required_count]

        min_duration = float('inf')
        for video in selected_videos:
            duration = get_video_duration(video)
            if duration:
                min_duration = min(min_duration, duration)

        if min_duration == float('inf'):
            min_duration = 10.0

        print(f"最短视频时长: {min_duration} 秒")

        base_width, base_height = get_video_resolution(selected_videos[0])
        if not base_width or not base_height:
            base_width, base_height = 1920, 1080

        cell_width = base_width // self.cols
        cell_height = base_height // self.rows

        output_width = cell_width * self.cols
        output_height = cell_height * self.rows

        random_name = random_with_system_time()
        output_video = os.path.join(video_output_dir, f"grid-{self.layout}-{random_name}.mp4")

        scaled_videos = []
        for i, video in enumerate(selected_videos):
            scaled_video = generate_temp_filename(video, f"_scaled_{i}.mp4", work_output_dir)
            self._scale_video(video, scaled_video, cell_width, cell_height)
            scaled_videos.append(scaled_video)

        if self.layout == '4grid':
            final_video = self._create_4grid(scaled_videos, output_width, output_height, min_duration, output_video)
        else:
            final_video = self._create_9grid(scaled_videos, output_width, output_height, min_duration, output_video)

        if final_video and os.path.exists(final_video) and os.path.getsize(final_video) == 0:
            print(f"错误: 宫格视频 {final_video} 为空，生成失败")
            return None

        for scaled in scaled_videos:
            if os.path.exists(scaled):
                try:
                    os.remove(scaled)
                except:
                    pass

        if final_video and self.background_music and os.path.exists(self.background_music):
            final_video = self._add_background_music(final_video, self.background_music, min_duration)

        return final_video

    def _scale_video(self, input_video, output_video, width, height):
        """缩放视频到指定尺寸"""
        command = [
            'ffmpeg',
            '-i', input_video,
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}',
            '-r', str(self.fps),
            '-c:v', 'libx264', '-preset', 'fast',
            '-y',
            output_video
        ]
        print("缩放视频:", " ".join(command))
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"缩放视频失败: {result.stderr}")

    def _create_4grid(self, scaled_videos, output_width, output_height, duration, output_video):
        """创建4宫格视频"""
        left_top = scaled_videos[0]
        right_top = scaled_videos[1]
        left_bottom = scaled_videos[2]
        right_bottom = scaled_videos[3]

        filter_complex = f"""
        [0:v]setpts=PTS-STARTPTS[left_top];
        [1:v]setpts=PTS-STARTPTS[right_top];
        [2:v]setpts=PTS-STARTPTS[left_bottom];
        [3:v]setpts=PTS-STARTPTS[right_bottom];
        [left_top][right_top]hstack=inputs=2[top_row];
        [left_bottom][right_bottom]hstack=inputs=2[bottom_row];
        [top_row][bottom_row]vstack=inputs=2[out]
        """

        command = [
            'ffmpeg',
            '-i', left_top,
            '-i', right_top,
            '-i', left_bottom,
            '-i', right_bottom,
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-t', str(duration),
            '-r', str(self.fps),
            '-c:v', 'libx264', '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            '-y',
            output_video
        ]
        print("创建4宫格:", " ".join(command))
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"创建4宫格失败: {result.stderr}")

        return output_video if os.path.exists(output_video) else None

    def _create_9grid(self, scaled_videos, output_width, output_height, duration, output_video):
        """创建9宫格视频"""
        v1 = scaled_videos[0]
        v2 = scaled_videos[1]
        v3 = scaled_videos[2]
        v4 = scaled_videos[3]
        v5 = scaled_videos[4]
        v6 = scaled_videos[5]
        v7 = scaled_videos[6]
        v8 = scaled_videos[7]
        v9 = scaled_videos[8]

        filter_complex = f"""
        [0:v]setpts=PTS-STARTPTS[v1];
        [1:v]setpts=PTS-STARTPTS[v2];
        [2:v]setpts=PTS-STARTPTS[v3];
        [3:v]setpts=PTS-STARTPTS[v4];
        [4:v]setpts=PTS-STARTPTS[v5];
        [5:v]setpts=PTS-STARTPTS[v6];
        [6:v]setpts=PTS-STARTPTS[v7];
        [7:v]setpts=PTS-STARTPTS[v8];
        [8:v]setpts=PTS-STARTPTS[v9];
        [v1][v2][v3]hstack=inputs=3[row1];
        [v4][v5][v6]hstack=inputs=3[row2];
        [v7][v8][v9]hstack=inputs=3[row3];
        [row1][row2][row3]vstack=inputs=3[out]
        """

        command = [
            'ffmpeg',
            '-i', v1,
            '-i', v2,
            '-i', v3,
            '-i', v4,
            '-i', v5,
            '-i', v6,
            '-i', v7,
            '-i', v8,
            '-i', v9,
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-t', str(duration),
            '-r', str(self.fps),
            '-c:v', 'libx264', '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            '-y',
            output_video
        ]
        print("创建9宫格:", " ".join(command))
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"创建9宫格失败: {result.stderr}")

        return output_video if os.path.exists(output_video) else None

    def _add_background_music(self, video_file, audio_file, duration):
        """添加背景音乐"""
        output_file = generate_temp_filename(video_file, "_with_bgm.mp4", work_output_dir)

        if os.path.getsize(video_file) == 0:
            print(f"错误: 视频文件 {video_file} 为空，bgm 添加失败")
            return video_file

        check_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', video_file]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        has_audio = 'audio' in check_result.stdout

        if has_audio:
            filter_complex = f'[1:a]aloop=loop=0:size=100M,volume={self.bgm_volume}[bgm];[0:a][bgm]amix=duration=first:dropout_transition=3:inputs=2[a]'
            map_audio = '[a]'
        else:
            filter_complex = f'[1:a]aloop=loop=0:size=100M,volume={self.bgm_volume}[bgm];anullsrc=r=44100:cl=stereo[silent];[silent][bgm]amix=duration=first:dropout_transition=3:inputs=2[a]'
            map_audio = '[a]'

        command = [
            'ffmpeg',
            '-i', video_file,
            '-i', audio_file,
            '-filter_complex', filter_complex,
            '-map', '0:v',
            '-map', map_audio,
            '-t', str(duration),
            '-c:v', 'copy',
            '-shortest',
            '-y',
            output_file
        ]
        print("添加背景音乐:", " ".join(command))
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"添加背景音乐失败: {result.stderr}")
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except:
                    pass
            return video_file

        if os.path.exists(output_file):
            try:
                os.remove(video_file)
            except:
                pass
            try:
                os.rename(output_file, video_file)
            except:
                pass

        print(f"最终视频已生成: {video_file}")
        return video_file
