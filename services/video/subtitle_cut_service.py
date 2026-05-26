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

import csv
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import timedelta

import streamlit as st

from services.captioning.captioning_service import add_subtitles
from tools.file_utils import generate_temp_filename
from tools.utils import random_with_system_time


script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
video_output_dir = os.path.join(script_dir, "../../final")
video_output_dir = os.path.abspath(video_output_dir)
work_output_dir = os.path.join(script_dir, "../../work")
work_output_dir = os.path.abspath(work_output_dir)


@dataclass
class SubtitleSegment:
    """字幕片段数据结构"""
    index: int
    start_time: str  # 字幕时间轴开始，如 "00:00:00"
    end_time: str    # 字幕时间轴结束，如 "00:00:15"
    duration: int    # 时长（秒）
    narration: str   # 解说文案
    source_timecode: str  # 原片截取时间码，如 "00:00:00 → 00:00:15"


def parse_timestamp(ts: str) -> float:
    """将时间戳字符串转换为秒数
    
    Args:
        ts: 时间戳字符串，格式如 "00:00:00" 或 "00:00:00,000"
    Returns:
        秒数
    """
    ts = ts.strip().replace(',', '.')
    parts = ts.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    return 0.0


def seconds_to_srt_time(seconds: float) -> str:
    """将秒数转换为SRT格式时间
    
    Args:
        seconds: 秒数
    Returns:
        SRT格式时间字符串，如 "00:00:00,000"
    """
    td = timedelta(seconds=seconds)
    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)
    secs = td.total_seconds() % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')


def seconds_to_hhmmss(seconds: float) -> str:
    """将秒数转换为 HH:MM:SS 格式
    
    Args:
        seconds: 秒数
    Returns:
        HH:MM:SS 格式字符串
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_timecode_range(timecode_str: str) -> tuple:
    """解析时间码范围字符串
    
    Args:
        timecode_str: 时间码范围，如 "00:21:00 → 00:21:40" 或 "首选：00:21:00 → 00:21:40 高清巨轮起航"
    Returns:
        (start_seconds, end_seconds)
    """
    # 使用正则表达式匹配 HH:MM:SS 或 HH:MM:SS.mmm 格式的时间码
    time_pattern = r'(\d{1,2}:\d{2}:\d{2}(?:\.\d+)?)'
    
    # 查找所有时间码
    matches = re.findall(time_pattern, timecode_str)
    
    if len(matches) >= 2:
        start_str = matches[0]
        end_str = matches[1]
        return parse_timestamp(start_str), parse_timestamp(end_str)
    
    return 0.0, 0.0


def parse_subtitle_timeline(timeline: str) -> tuple:
    """解析字幕时间轴
    
    Args:
        timeline: 时间轴字符串，如 "00:00:00 → 00:00:15"
    Returns:
        (start_time, end_time)
    """
    parts = timeline.split('→')
    if len(parts) != 2:
        parts = timeline.split('->')
    
    if len(parts) == 2:
        start = parts[0].strip()
        end = parts[1].strip()
        return start, end
    
    return "", ""


def parse_csv_subtitle(csv_path: str) -> list:
    """解析CSV字幕文件
    
    Args:
        csv_path: CSV文件路径
    Returns:
        SubtitleSegment列表
    """
    segments = []
    
    if not os.path.exists(csv_path):
        print(f"CSV文件不存在: {csv_path}")
        return segments
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # 跳过标题行
            
            for row in reader:
                if len(row) < 5:
                    continue
                
                try:
                    index = int(row[0].strip())
                    timeline = row[1].strip()
                    duration_str = row[2].strip()
                    narration = row[3].strip()
                    source_timecode = row[4].strip()
                    
                    # 解析时长
                    duration = 0
                    if '秒' in duration_str:
                        duration = int(duration_str.replace('秒', ''))
                    elif duration_str.isdigit():
                        duration = int(duration_str)
                    
                    # 解析时间轴
                    start_time, end_time = parse_subtitle_timeline(timeline)
                    
                    segment = SubtitleSegment(
                        index=index,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        narration=narration,
                        source_timecode=source_timecode
                    )
                    segments.append(segment)
                    
                except (ValueError, IndexError) as e:
                    print(f"解析行失败: {row}, 错误: {e}")
                    continue
                    
    except Exception as e:
        print(f"读取CSV文件失败: {e}")
    
    return segments


def get_video_info(video_file: str) -> dict:
    """获取视频信息
    
    Args:
        video_file: 视频文件路径
    Returns:
        包含视频信息的字典
    """
    info = {
        'duration': 0,
        'width': 0,
        'height': 0,
        'fps': 30
    }
    
    try:
        # 获取时长
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
               '-of', 'default=noprint_wrappers=1:nokey=1', video_file]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode == 0 and result.stdout.strip():
            info['duration'] = float(result.stdout.strip())
        
        # 获取分辨率
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
               '-show_entries', 'stream=width,height,r_frame_rate',
               '-of', 'csv=p=0', video_file]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(',')
            if len(parts) >= 2:
                info['width'] = int(parts[0])
                info['height'] = int(parts[1])
            if len(parts) >= 3:
                fps_parts = parts[2].split('/')
                if len(fps_parts) == 2:
                    info['fps'] = float(fps_parts[0]) / float(fps_parts[1])
                else:
                    info['fps'] = float(parts[2])
                    
    except Exception as e:
        print(f"获取视频信息失败: {e}")
    
    return info


def cut_video_segment(video_file: str, start_time: float, end_time: float,
                     output_file: str = None, fps: int = 30) -> str:
    """从视频中剪切指定时间段

    Args:
        video_file: 源视频文件路径
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        output_file: 输出文件路径（可选）
        fps: 输出帧率
    Returns:
        输出文件路径
    """
    if output_file is None:
        output_file = generate_temp_filename(video_file, "_cut.mp4", work_output_dir)

    duration = end_time - start_time

    command = [
        'ffmpeg', '-ss', str(start_time),
        '-i', video_file,
        '-t', str(duration),
        '-r', str(fps),
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'aac',
        '-movflags', '+faststart',
        '-y', output_file
    ]

    print(f"剪切视频片段: {video_file} [{start_time:.2f}s - {end_time:.2f}s]")
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')

    if result.returncode != 0:
        print(f"剪切失败: {result.stderr}")
        return None

    return output_file


def generate_srt_file(segments: list, output_file: str) -> str:
    """生成SRT字幕文件

    Args:
        segments: SubtitleSegment列表
        output_file: 输出文件路径
    Returns:
        输出文件路径
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, 1):
            # 计算在最终视频中的时间位置
            # 需要累计前面所有片段的时长
            start_seconds = 0
            for j in range(segment.index - 1):
                if j < len(segments):
                    start_seconds += segments[j].duration

            end_seconds = start_seconds + segment.duration

            # 写入SRT格式
            f.write(f"{i}\n")
            f.write(f"{seconds_to_srt_time(start_seconds)} --> {seconds_to_srt_time(end_seconds)}\n")
            f.write(f"{segment.narration}\n")
            f.write("\n")

    print(f"SRT字幕文件已生成: {output_file}")
    return output_file


def generate_srt_file_for_segments(all_segments: list, used_segments: list, output_file: str, max_duration: int = None) -> str:
    """为使用的片段生成SRT字幕文件

    Args:
        all_segments: 所有字幕片段列表
        used_segments: 实际使用的片段信息列表
        output_file: 输出文件路径
        max_duration: 最大时长限制
    Returns:
        输出文件路径
    """
    if not used_segments:
        print("没有使用的片段，跳过字幕生成")
        return None

    # 创建片段索引到实际片段的映射
    segment_map = {seg.index: seg for seg in all_segments}

    with open(output_file, 'w', encoding='utf-8') as f:
        subtitle_index = 1
        current_time = 0

        for used in used_segments:
            seg = segment_map.get(used['index'])
            if not seg:
                continue

            start_seconds = current_time
            end_seconds = current_time + used['duration']

            # 写入SRT格式
            f.write(f"{subtitle_index}\n")
            f.write(f"{seconds_to_srt_time(start_seconds)} --> {seconds_to_srt_time(end_seconds)}\n")
            f.write(f"{seg.narration}\n")
            f.write("\n")

            subtitle_index += 1
            current_time = end_seconds

    print(f"SRT字幕文件已生成（{len(used_segments)}个片段）: {output_file}")
    return output_file


class SubtitleCutService:
    """基于字幕的电影视频剪切服务"""

    def __init__(self, video_file: str, csv_path: str, fps: int = 30, max_duration: int = None):
        """
        初始化服务

        Args:
            video_file: 源电影视频文件路径
            csv_path: CSV字幕文件路径
            fps: 输出视频帧率
            max_duration: 最大时长限制（秒），None表示不限制
        """
        self.video_file = video_file
        self.csv_path = csv_path
        self.fps = fps
        self.max_duration = max_duration

        # 获取视频信息
        self.video_info = get_video_info(video_file)

        # 解析字幕
        self.segments = parse_csv_subtitle(csv_path)

        print(f"已加载 {len(self.segments)} 个字幕片段")
    
    def get_segments(self) -> list:
        """获取字幕片段列表"""
        return self.segments
    
    def get_total_duration(self) -> float:
        """获取总时长"""
        return sum(seg.duration for seg in self.segments)
    
    def validate_timecodes(self) -> dict:
        """验证时间码是否在视频范围内
        
        Returns:
            验证结果字典，包含有效性和错误信息
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        video_duration = self.video_info['duration']
        
        for segment in self.segments:
            start, end = parse_timecode_range(segment.source_timecode)
            duration = end - start
            
            if end > video_duration:
                result['valid'] = False
                result['errors'].append(
                    f"片段 {segment.index}: 结束时间 {end:.2f}s 超过视频时长 {video_duration:.2f}s"
                )
            
            if duration < 1:
                result['warnings'].append(
                    f"片段 {segment.index}: 时长过短 ({duration:.2f}s)"
                )
        
        return result
    
    def cut_all_segments(self, progress_callback=None) -> tuple:
        """剪切所有视频片段

        Args:
            progress_callback: 进度回调函数
        Returns:
            (cut_files, used_segments) - 剪切后的视频片段路径列表和使用的片段信息
        """
        cut_files = []
        used_segments = []
        total_duration = 0

        for i, segment in enumerate(self.segments):
            # 检查是否超过最大时长限制
            if self.max_duration is not None and total_duration >= self.max_duration:
                print(f"已达到最大时长限制 {self.max_duration} 秒，停止剪切")
                break

            start, end = parse_timecode_range(segment.source_timecode)
            seg_duration = end - start

            # 如果这个片段会导致超过限制，尝试截断
            if self.max_duration is not None and total_duration + seg_duration > self.max_duration:
                # 计算还能使用的时长
                remaining = self.max_duration - total_duration
                if remaining < 1:  # 剩余时间太少就停止
                    break
                # 调整结束时间
                end = start + remaining
                seg_duration = remaining
                print(f"片段 {segment.index} 截断为 {remaining:.1f} 秒以符合时长限制")

            output_file = os.path.join(work_output_dir, f"segment_{segment.index:02d}.mp4")
            result = cut_video_segment(
                self.video_file, start, end, output_file, self.fps
            )

            if result and os.path.exists(result):
                cut_files.append(result)
                used_segments.append({
                    'index': segment.index,
                    'start': start,
                    'end': end,
                    'duration': seg_duration
                })
                total_duration += seg_duration
            else:
                print(f"片段 {segment.index} 剪切失败")

            if progress_callback:
                progress_callback((i + 1) / len(self.segments))

        return cut_files, used_segments
    
    def concatenate_videos(self, video_files: list, output_file: str = None) -> str:
        """拼接视频片段
        
        Args:
            video_files: 视频文件路径列表
            output_file: 输出文件路径
        Returns:
            拼接后的视频文件路径
        """
        if not video_files:
            return None
        
        if output_file is None:
            random_name = random_with_system_time()
            output_file = os.path.join(video_output_dir, f"concatenated-{random_name}.mp4")
        
        # 创建文件列表
        list_file = os.path.join(work_output_dir, "concat_list.txt")
        with open(list_file, 'w', encoding='utf-8') as f:
            for video in video_files:
                f.write(f"file '{video}'\n")
        
        # 拼接视频
        command = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', list_file,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac',
            '-movflags', '+faststart',
            '-y', output_file
        ]
        
        print(f"拼接 {len(video_files)} 个视频片段")
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        # 清理临时文件
        try:
            os.remove(list_file)
        except:
            pass
        
        if result.returncode != 0:
            print(f"拼接失败: {result.stderr}")
            return None
        
        return output_file
    
    def generate_final_video(self, add_subtitle: bool = True,
                            subtitle_style: dict = None,
                            progress_callback=None) -> str:
        """生成最终视频

        Args:
            add_subtitle: 是否添加字幕
            subtitle_style: 字幕样式配置
            progress_callback: 进度回调函数
        Returns:
            最终视频文件路径
        """
        if not self.segments:
            print("没有字幕片段")
            return None

        # 1. 剪切所有片段
        if progress_callback:
            progress_callback(0.1)
            print("正在剪切视频片段...")

        cut_result = self.cut_all_segments()
        cut_files = cut_result[0] if isinstance(cut_result, tuple) else cut_result
        used_segments = cut_result[1] if isinstance(cut_result, tuple) else None

        if not cut_files:
            print("视频剪切失败")
            return None

        print(f"共剪切了 {len(cut_files)} 个视频片段")

        # 2. 拼接视频
        if progress_callback:
            progress_callback(0.5)
            print("正在拼接视频...")

        random_name = random_with_system_time()
        merged_file = os.path.join(video_output_dir, f"merged-{random_name}.mp4")
        merged_video = self.concatenate_videos(cut_files, merged_file)

        if not merged_video:
            print("视频拼接失败")
            return None

        # 清理临时片段（在拼接成功后才清理）
        if merged_video and os.path.exists(merged_video):
            for f in cut_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except:
                    pass

        # 3. 添加字幕
        final_video = merged_video
        if add_subtitle:
            if progress_callback:
                progress_callback(0.8)
                print("正在添加字幕...")

            # 生成SRT字幕文件（只对使用的片段生成字幕）
            srt_file = os.path.join(work_output_dir, f"subtitle-{random_name}.srt")
            generate_srt_file_for_segments(self.segments, used_segments, srt_file, self.max_duration)

            # 应用字幕样式
            if subtitle_style is None:
                subtitle_style = {}

            font_name = subtitle_style.get('font', st.session_state.get('subtitle_font', '微软雅黑'))
            font_size = subtitle_style.get('font_size', st.session_state.get('subtitle_font_size', 48))
            primary_colour = subtitle_style.get('color', st.session_state.get('subtitle_color', '#FFFFFF'))
            outline_colour = subtitle_style.get('border_color', st.session_state.get('subtitle_border_color', '#000000'))
            outline = subtitle_style.get('border_width', st.session_state.get('subtitle_border_width', 3))
            alignment = subtitle_style.get('position', st.session_state.get('subtitle_position', 2))

            # 添加字幕到视频（捕获异常，防止字幕失败导致整个视频无法使用）
            try:
                print(f"正在烧录字幕到视频: {merged_video}")
                print(f"字幕文件: {srt_file}")
                add_subtitles(
                    merged_video, srt_file,
                    font_name=font_name,
                    font_size=font_size,
                    primary_colour=primary_colour,
                    outline_colour=outline_colour,
                    outline=outline,
                    alignment=alignment
                )
                print("字幕添加完成")
            except Exception as e:
                print(f"字幕添加失败: {e}")
                print("视频已生成但未添加字幕，可以手动使用其他工具添加字幕")

            # 清理临时文件
            try:
                if os.path.exists(srt_file):
                    os.remove(srt_file)
            except:
                pass

            # 检查 merged_video 是否还存在，如果被删除了说明字幕处理成功（会重命名回来）
            # 如果不存在，说明字幕处理可能出问题了，使用备选方案
            if not os.path.exists(merged_video):
                # 字幕处理成功，找回重命名后的文件
                if os.path.exists(merged_video):
                    final_video = merged_video
                else:
                    # 尝试在 final 目录查找最新的 mp4 文件
                    import glob
                    latest_files = glob.glob(os.path.join(video_output_dir, "*.mp4"))
                    if latest_files:
                        final_video = max(latest_files, key=os.path.getctime)
                        print(f"找回字幕处理后的视频: {final_video}")

        if progress_callback:
            progress_callback(1.0)

        return final_video


def create_subtitle_cut_service(video_file: str, csv_path: str, fps: int = 30) -> SubtitleCutService:
    """便捷函数：创建字幕剪切服务"""
    return SubtitleCutService(video_file, csv_path, fps)
