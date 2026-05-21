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

    # 滤镜预设
    FILTER_PRESETS = {
        "none": "",
        "light": "eq=saturation=1.1:contrast=1.05:brightness=0.02",
        "medium": "eq=saturation=1.2:contrast=1.1:brightness=0.03",
        "strong": "eq=saturation=1.3:contrast=1.15:brightness=0.05:hue=s+5",
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

    def _run_ffmpeg(self, command, desc=""):
        """执行 FFmpeg 命令并返回是否成功"""
        print(f"{desc}: {' '.join(command[:5])}...")
        success = run_ffmpeg_command(command)
        return success

    def apply_random_start_point(self, video_file, max_offset=2.0, max_duration=5.0):
        """从视频随机位置开始截取"""
        from services.video.video_service import get_video_duration

        duration = get_video_duration(video_file)

        # 计算最大允许的起始位置
        max_start = min(max_offset, duration - max_duration)
        if max_start <= 0:
            # 如果原视频小于等于max_duration，直接使用原视频
            if duration <= max_duration:
                return video_file
            # 否则从开头截取
            start_point = 0
        else:
            start_point = random.uniform(0, max_start)

        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        command = [
            'ffmpeg', '-ss', str(start_point), '-t', str(max_duration),
            '-i', video_file, '-c:v', 'libx264', '-preset', 'fast', '-y', output_file
        ]

        print(f"随机起点截取: 起始={start_point:.2f}秒, 时长={max_duration}秒")
        if self._run_ffmpeg(command, "截取"):
            return output_file
        return video_file

    def apply_speed_change(self, video_file, speed_factor=1.0):
        """
        变速处理
        speed_factor: 速度因子，如 1.05 表示加速5%，0.95 表示减速5%
        """
        if speed_factor == 1.0:
            return video_file

        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        # setpts: >1 减速，<1 加速
        filter_str = f"setpts=PTS/{speed_factor}"

        command = [
            'ffmpeg', '-i', video_file,
            '-vf', filter_str,
            '-c:a', 'aformat=sample_fmts=fltp:sample_rates=44100|48000',
            '-y', output_file
        ]

        print(f"变速处理: 速度因子={speed_factor} ({'加速' if speed_factor > 1 else '减速'}{abs(speed_factor-1)*100:.0f}%)")
        if self._run_ffmpeg(command, "变速"):
            return output_file
        return video_file

    def apply_mirror(self, video_file, direction="horizontal"):
        """
        镜像翻转
        direction: "horizontal" 水平镜像, "vertical" 垂直镜像, "both" 两者都有
        """
        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        if direction == "horizontal":
            filter_str = "hflip"
        elif direction == "vertical":
            filter_str = "vflip"
        else:
            filter_str = "hflip,vflip"

        command = [
            'ffmpeg', '-i', video_file,
            '-vf', filter_str, '-c:a', 'copy', '-y', output_file
        ]

        print(f"镜像翻转: {direction}")
        if self._run_ffmpeg(command, "镜像"):
            return output_file
        return video_file

    def apply_random_crop(self, video_file, scale_range=(0.95, 1.05)):
        """
        随机画面缩放
        scale_range: 缩放范围元组 (min, max)
        """
        scale_factor = random.uniform(scale_range[0], scale_range[1])

        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        # 先缩放再裁剪回原尺寸，同时修复宽高比
        filter_str = f"scale=iw*{scale_factor}:ih*{scale_factor},crop=iw:ih,setsar=1"

        command = [
            'ffmpeg', '-i', video_file,
            '-vf', filter_str, '-c:a', 'copy', '-y', output_file
        ]

        print(f"随机缩放: 比例={scale_factor:.2f}")
        if self._run_ffmpeg(command, "缩放"):
            return output_file
        return video_file

    def apply_noise(self, video_file, intensity=15):
        """
        添加轻微噪点
        intensity: 噪点强度 (5-30)
        """
        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        filter_str = f"noise=alls={intensity}:allf=t+u"

        command = [
            'ffmpeg', '-i', video_file,
            '-vf', filter_str, '-c:a', 'copy', '-y', output_file
        ]

        print(f"添加噪点: 强度={intensity}")
        if self._run_ffmpeg(command, "噪点"):
            return output_file
        return video_file

    def apply_speed_ramp(self, video_file, ramp_type="ease_in_out"):
        """
        速度渐变
        ramp_type: "ease_in" 开始慢后快, "ease_out" 开始快后慢, "ease_in_out" 慢-快-慢
        """
        from services.video.video_service import get_video_duration

        duration = get_video_duration(video_file)
        if duration is None or duration <= 0:
            return video_file

        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        # 将视频分成3段处理
        seg1_dur = duration * 0.2  # 前20%
        seg2_dur = duration * 0.6  # 中间60%
        seg3_dur = duration * 0.2  # 后20%

        temp1 = generate_temp_filename(video_file, "_seg1.mp4", self.work_output_dir)
        temp2 = generate_temp_filename(video_file, "_seg2.mp4", self.work_output_dir)

        try:
            # 第一段：慢速
            if ramp_type in ["ease_in", "ease_in_out"]:
                cmd1 = ['ffmpeg', '-i', video_file, '-t', str(seg1_dur),
                        '-vf', 'setpts=PTS*1.3', '-y', temp1]
                self._run_ffmpeg(cmd1, "速度渐变-第一段")
            else:
                cmd1 = ['ffmpeg', '-i', video_file, '-t', str(seg1_dur), '-c', 'copy', '-y', temp1]
                self._run_ffmpeg(cmd1, "速度渐变-第一段")

            # 第二段：正常速度
            offset2 = seg1_dur
            cmd2 = ['ffmpeg', '-ss', str(offset2), '-i', video_file, '-t', str(seg2_dur),
                    '-c', 'copy', '-y', temp2]
            self._run_ffmpeg(cmd2, "速度渐变-第二段")

            # 第三段：慢速
            temp3 = generate_temp_filename(video_file, "_seg3.mp4", self.work_output_dir)
            offset3 = seg1_dur + seg2_dur
            if ramp_type in ["ease_out", "ease_in_out"]:
                cmd3 = ['ffmpeg', '-ss', str(offset3), '-i', video_file,
                        '-vf', 'setpts=PTS*1.3', '-y', temp3]
                self._run_ffmpeg(cmd3, "速度渐变-第三段")
            else:
                cmd3 = ['ffmpeg', '-ss', str(offset3), '-i', video_file, '-c', 'copy', '-y', temp3]
                self._run_ffmpeg(cmd3, "速度渐变-第三段")

            # 合并三段
            concat_list = generate_temp_filename(video_file, "_concat.txt", self.work_output_dir)
            with open(concat_list, 'w') as f:
                f.write(f"file '{temp1}'\n")
                f.write(f"file '{temp2}'\n")
                f.write(f"file '{temp3}'\n")

            cmd_concat = ['ffmpeg', '-f', 'concat', '-safe', '0',
                          '-i', concat_list, '-c', 'copy', '-y', output_file]
            self._run_ffmpeg(cmd_concat, "速度渐变-合并")

            # 清理临时文件
            for f in [temp1, temp2, temp3, concat_list]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

            if os.path.exists(output_file):
                print(f"速度渐变完成: {ramp_type}")
                return output_file

        except Exception as e:
            print(f"速度渐变失败: {e}")

        return video_file

    def apply_filter(self, video_file, filter_preset="light"):
        """应用色彩滤镜"""
        if filter_preset == "none" or not filter_preset:
            return video_file

        filter_str = self.FILTER_PRESETS.get(filter_preset, self.FILTER_PRESETS["light"])
        if not filter_str:
            return video_file

        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        command = [
            'ffmpeg', '-i', video_file,
            '-vf', f"{filter_str},setsar=1",
            '-c:a', 'copy', '-y', output_file
        ]

        print(f"应用滤镜: {filter_preset}")
        if self._run_ffmpeg(command, "滤镜"):
            return output_file
        return video_file

    def add_watermark(self, video_file, watermark_path, position="bottom_right",
                      opacity=0.7, scale=0.15):
        """添加水印"""
        if not watermark_path or not os.path.exists(watermark_path):
            print(f"水印文件不存在: {watermark_path}")
            return video_file

        overlay_pos = self.WATERMARK_POSITIONS.get(position, self.WATERMARK_POSITIONS["bottom_right"])

        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        command = [
            'ffmpeg', '-i', video_file, '-i', watermark_path,
            '-filter_complex',
            f"[1:v]scale=iw*{scale}:-1,format=rgba,colorchannelmixer=aa={opacity}[wm];"
            f"[0:v][wm]overlay={overlay_pos},setsar=1[out]",
            '-map', '[out]', '-map', '0:a?', '-y', output_file
        ]

        print(f"添加水印: 位置={position}")
        if self._run_ffmpeg(command, "水印"):
            return output_file
        return video_file

    def remove_audio(self, video_file):
        """移除原音"""
        output_file = generate_temp_filename(video_file, ".mp4", self.work_output_dir)

        command = [
            'ffmpeg', '-i', video_file,
            '-an', '-c:v', 'copy', '-y', output_file
        ]

        print("移除原音")
        if self._run_ffmpeg(command, "静音"):
            return output_file
        return video_file

    def process_video(self, video_file,
                      # 随机起点
                      enable_random_start=True, max_offset=2.0, max_duration=5.0,
                      # 变速
                      enable_speed_change=False, speed_range=(0.92, 1.08),
                      # 镜像
                      enable_mirror=False, mirror_direction="horizontal",
                      # 缩放
                      enable_random_crop=False, crop_scale_range=(0.95, 1.05),
                      # 噪点
                      enable_noise=False, noise_intensity=15,
                      # 速度渐变
                      enable_speed_ramp=False, speed_ramp_type="ease_in_out",
                      # 滤镜
                      filter_preset="none",
                      # 水印
                      watermark_path=None, watermark_position="bottom_right",
                      watermark_opacity=0.7, watermark_scale=0.15,
                      # 音频
                      remove_original_audio=False):
        """
        一站式处理视频：按顺序应用所有原创性提升处理

        处理顺序：随机起点 -> 变速 -> 镜像 -> 噪点 -> 滤镜 -> 缩放 -> 水印
        """
        current_file = video_file

        # 1. 随机起点截取
        if enable_random_start:
            current_file = self.apply_random_start_point(current_file, max_offset, max_duration)

        # 2. 速度渐变 (与变速互斥，优先级更高)
        if enable_speed_ramp:
            current_file = self.apply_speed_ramp(current_file, speed_ramp_type)
        # 3. 变速处理
        elif enable_speed_change:
            speed_factor = random.uniform(speed_range[0], speed_range[1])
            current_file = self.apply_speed_change(current_file, speed_factor)

        # 4. 镜像翻转
        if enable_mirror:
            current_file = self.apply_mirror(current_file, mirror_direction)

        # 5. 添加噪点
        if enable_noise:
            current_file = self.apply_noise(current_file, noise_intensity)

        # 6. 色彩滤镜
        if filter_preset and filter_preset != "none":
            current_file = self.apply_filter(current_file, filter_preset)

        # 7. 随机缩放
        if enable_random_crop:
            current_file = self.apply_random_crop(current_file, crop_scale_range)

        # 8. 水印添加
        if watermark_path:
            current_file = self.add_watermark(current_file, watermark_path,
                                             watermark_position, watermark_opacity, watermark_scale)

        # 9. 移除原音（最后处理，因为后续不需要音频）
        if remove_original_audio:
            current_file = self.remove_audio(current_file)

        return current_file


def enhance_video_originality(video_file, work_output_dir, **kwargs):
    """便捷函数：增强视频原创性"""
    service = OriginalityService(work_output_dir)
    return service.process_video(video_file, **kwargs)
