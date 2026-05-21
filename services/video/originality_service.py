#  Copyright © [2024] 程序那些事
#
#  All rights reserved. This software and associated documentation files (the "Software") are provided for personal and educational use only. Commercial use of the Software is strictly prohibited unless explicit permission is obtained from the author.
#
#  Permission is hereby granted to any person to use, copy, and modify the Software for non-commercial purposes, provided that the following conditions are met:
#
#  1. The original copyright notice and this permission notice must be included in all copies or substantial portions of the Software.
#  2. Modifications, if any must retain the original copyright information and must not imply that the modified version is an official version of the Software.
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

import os
import random

from tools.file_utils import generate_temp_filename
from tools.utils import run_ffmpeg_command


class OriginalityService:
    """视频原创性提升服务"""

    # 滤镜预设 - 从轻微到明显
    FILTER_PRESETS = {
        "none": "",  # 无滤镜
        "light": "eq=saturation=1.1:contrast=1.05:brightness=0.02",  # 轻微
        "medium": "eq=saturation=1.2:contrast=1.1:brightness=0.03",  # 中等
        "strong": "eq=saturation=1.3:contrast=1.15:brightness=0.05:hue=s+5",  # 明显
    }

    # 水印位置映射
    WATERMARK_POSITIONS = {
        "top_left": "10:10",
        "top_right": "W-w-10:10",
        "bottom_left": "10:H-h-10",
        "bottom_right": "W-w-10:H-h-10",
        "center": "(W-w)/2:(H-h)/2",
    }

    def __init__(self, work_output_dir):
        self.work_output_dir = work_output_dir
        self.random_seed = random.randint(0, 10000)

    def apply_random_start_point(self, video_file, max_offset=2.0, min_duration=8.0, max_duration=10.0):
        """
        从视频随机位置开始截取

        Args:
            video_file: 输入视频路径
            max_offset: 最大起始偏移（秒），默认2秒
            min_duration: 最小保留时长（秒），默认8秒
            max_duration: 最大截取时长（秒），默认10秒

        Returns:
            处理后的视频路径，如果不需要处理则返回原路径
        """
        from services.video.video_service import get_video_duration

        duration = get_video_duration(video_file)

        # 如果视频太短，不进行截取
        if duration <= min_duration:
            return video_file

        # 计算最大允许的起始位置，确保截取时长不超过max_duration
        max_start = min(max_offset, duration - min_duration, duration - max_duration)
        if max_start <= 0:
            # 如果起始位置已经是0，但原视频超过max_duration，则从开头截取max_duration
            if duration > max_duration:
                output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)
                command = [
                    'ffmpeg',
                    '-t', str(max_duration),
                    '-i', video_file,
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-y',
                    output_file
                ]
                print(f"截取固定时长: {max_duration}秒")
                run_ffmpeg_command(command)
                if not os.path.exists(output_file):
                    print("固定时长截取失败，返回原视频")
                    return video_file
                return output_file
            return video_file

        # 随机生成起始点
        start_point = random.uniform(0, max_start)
        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        command = [
            'ffmpeg',
            '-ss', str(start_point),
            '-t', str(max_duration),
            '-i', video_file,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-y',
            output_file
        ]

        print(f"随机起点截取: 起始={start_point:.2f}秒, 时长={max_duration}秒")
        success = run_ffmpeg_command(command)
        if not success or not os.path.exists(output_file):
            print("随机起点截取失败，返回原视频")
            return video_file
        return output_file

    def apply_filter(self, video_file, filter_preset="light"):
        """
        应用滤镜处理

        Args:
            video_file: 输入视频路径
            filter_preset: 滤镜预设 ("none", "light", "medium", "strong")

        Returns:
            处理后的视频路径，如果不需要处理则返回原路径
        """
        if filter_preset == "none" or not filter_preset:
            return video_file

        filter_str = self.FILTER_PRESETS.get(filter_preset, self.FILTER_PRESETS["light"])
        if not filter_str:
            return video_file

        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        command = [
            'ffmpeg',
            '-i', video_file,
            '-vf', filter_str,
            '-c:a', 'copy',
            '-y',
            output_file
        ]

        print(f"应用滤镜: {filter_preset} - {filter_str}")
        success = run_ffmpeg_command(command)
        if not success or not os.path.exists(output_file):
            print("滤镜处理失败，返回原视频")
            return video_file
        return output_file

    def add_watermark(self, video_file, watermark_path, position="bottom_right",
                      opacity=0.7, scale=0.15):
        """
        添加水印

        Args:
            video_file: 输入视频路径
            watermark_path: 水印图片路径
            position: 水印位置
            opacity: 透明度 (0-1)
            scale: 水印相对于视频宽度的比例

        Returns:
            处理后的视频路径，如果不需要处理则返回原路径
        """
        if not watermark_path or not os.path.exists(watermark_path):
            print(f"水印文件不存在: {watermark_path}")
            return video_file

        overlay_pos = self.WATERMARK_POSITIONS.get(position, self.WATERMARK_POSITIONS["bottom_right"])

        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        # 使用 colorchannelmixer 实现透明度调整
        command = [
            'ffmpeg',
            '-i', video_file,
            '-i', watermark_path,
            '-filter_complex',
            f"[1:v]scale=iw*{scale}:-1,format=rgba,colorchannelmixer=aa={opacity}[wm];"
            f"[0:v][wm]overlay={overlay_pos}[out]",
            '-map', '[out]',
            '-map', '0:a?',
            '-y',
            output_file
        ]

        print(f"添加水印: 位置={position}, 透明度={opacity}, 比例={scale}")
        success = run_ffmpeg_command(command)
        if not success or not os.path.exists(output_file):
            print("水印处理失败，返回原视频")
            return video_file
        return output_file

    def process_video(self, video_file, enable_random_start=True, max_offset=2.0,
                      max_duration=5.0, filter_preset="light", watermark_path=None,
                      watermark_position="bottom_right", watermark_opacity=0.7, watermark_scale=0.15):
        """
        一站式处理视频：随机起点 + 滤镜 + 水印

        Args:
            video_file: 输入视频路径
            enable_random_start: 是否启用随机起点
            max_offset: 最大起始偏移
            max_duration: 最大截取时长
            filter_preset: 滤镜预设
            watermark_path: 水印图片路径
            watermark_position: 水印位置
            watermark_opacity: 水印透明度
            watermark_scale: 水印大小比例

        Returns:
            处理后的视频路径
        """
        current_file = video_file

        # 1. 随机起点截取
        if enable_random_start:
            current_file = self.apply_random_start_point(current_file, max_offset, max_duration=max_duration)

        # 2. 滤镜处理
        if filter_preset and filter_preset != "none":
            current_file = self.apply_filter(current_file, filter_preset)

        # 3. 水印添加
        if watermark_path:
            current_file = self.add_watermark(current_file, watermark_path,
                                             watermark_position, watermark_opacity, watermark_scale)

        return current_file


def enhance_video_originality(video_file, work_output_dir, **kwargs):
    """
    便捷函数：增强视频原创性

    Args:
        video_file: 输入视频路径
        work_output_dir: 临时文件输出目录
        **kwargs: OriginalityService 的参数

    Returns:
        处理后的视频路径
    """
    service = OriginalityService(work_output_dir)
    return service.process_video(video_file, **kwargs)
