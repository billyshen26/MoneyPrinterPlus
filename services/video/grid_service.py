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
import re
import subprocess

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from tools.file_utils import generate_temp_filename
from tools.utils import random_with_system_time

script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
video_output_dir = os.path.join(script_dir, "../../final")
video_output_dir = os.path.abspath(video_output_dir)
work_output_dir = os.path.join(script_dir, "../../work")
work_output_dir = os.path.abspath(work_output_dir)


_selected_video_set = set()
_folder_key = None
_used_videos_file = os.path.join(script_dir, "../../config/used_videos.json")


def reset_video_selection():
    """重置视频选择状态，切换文件夹时调用"""
    global _selected_video_set, _folder_key
    _selected_video_set.clear()
    _folder_key = None
    import streamlit as st
    st.session_state.pop('_grid_selected_videos', None)


def _persist_selection():
    """将已选视频记录写入 session_state"""
    import streamlit as st
    st.session_state['_grid_selected_videos'] = list(_selected_video_set)


def _load_selection():
    """从 session_state 恢复已选视频记录"""
    import streamlit as st
    if '_grid_selected_videos' in st.session_state:
        _selected_video_set.update(st.session_state['_grid_selected_videos'])


def load_used_videos():
    """从文件加载已使用的视频记录"""
    import json
    used_videos = set()
    if os.path.exists(_used_videos_file):
        try:
            with open(_used_videos_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                used_videos = set(data.get('used_videos', []))
        except Exception as e:
            print(f"加载已使用视频失败: {e}")
    return used_videos


def save_used_videos(used_videos):
    """保存已使用的视频记录到文件"""
    import json
    try:
        os.makedirs(os.path.dirname(_used_videos_file), exist_ok=True)
        with open(_used_videos_file, 'w', encoding='utf-8') as f:
            json.dump({'used_videos': list(used_videos)}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存已使用视频失败: {e}")


def mark_videos_as_used(video_paths):
    """标记视频为已使用"""
    used_videos = load_used_videos()
    for video_path in video_paths:
        used_videos.add(os.path.abspath(video_path))
    save_used_videos(used_videos)


def get_available_videos(folder_path):
    """获取可用视频（排除已使用的）"""
    all_videos = get_video_files_from_folder(folder_path)
    used_videos = load_used_videos()
    available = [v for v in all_videos if os.path.abspath(v) not in used_videos]
    return available


def reset_used_videos():
    """重置已使用视频记录（清空记录）"""
    save_used_videos(set())
    print("已重置视频使用记录")


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
    try:
        command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                   '-of', 'default=noprint_wrappers=1:nokey=1', video_file]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"ffprobe 错误: {result.stderr}")
            return None
        output = result.stdout.strip()
        if not output:
            print(f"ffprobe 无输出 for: {video_file}")
            return None
        duration = float(output)
        return duration if duration > 0 else None
    except Exception as e:
        print(f"获取视频时长异常: {e}")
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


def extract_username_from_filename(filename):
    """从文件名中提取用户名，格式: fav_用户名_ID.mp4"""
    basename = os.path.basename(filename)
    m = re.match(r'fav_(.+?)_\d+\.mp4$', basename)
    if m:
        return m.group(1)
    return None


class VideoGridService:
    def __init__(self, video_list, layout='4grid', background_music=None, bgm_volume=0.3, video_folder=None):
        self.video_list = video_list
        self.layout = layout
        self.background_music = background_music
        self.bgm_volume = bgm_volume
        self.video_folder = video_folder

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
        _load_selection()

        if self.video_folder:
            current_key = self.video_folder
        else:
            current_key = None

        global _selected_video_set, _folder_key
        if _folder_key != current_key:
            _selected_video_set.clear()
            _folder_key = current_key
            _persist_selection()

        # 直接获取可用视频
        if self.layout == '4grid':
            required = 4
        else:
            required = 9
            
        available = [v for v in self.video_list if v not in _selected_video_set]
        if len(available) < required:
            print(f"可用视频不足，需要 {required} 个，已选过 {len(_selected_video_set)} 个")
            return None

        # 随机选择所需数量的视频
        selected_videos = random.sample(available, required)
        
        _selected_video_set.update(selected_videos)
        _persist_selection()
        print(f"本轮选中 {len(selected_videos)} 个视频")

        # 执行宫格合成
        result = self._do_grid(selected_videos)
        if result is None:
            return None
        final_video, usernames_file = result
        if final_video and os.path.exists(final_video):
            st.session_state['_grid_usernames_file'] = usernames_file
            # 根据开关决定是否标记视频为已使用
            allow_reuse = st.session_state.get('video_grid_allow_reuse', False)
            if not allow_reuse:
                mark_videos_as_used(selected_videos)
                print(f"已记录 {len(selected_videos)} 个视频为已使用")
        return final_video

    def _do_grid(self, selected_videos):
        """执行宫格合成"""
        usernames = [extract_username_from_filename(v) for v in selected_videos]
        usernames = [u for u in usernames if u]

        base_width, base_height = get_video_resolution(selected_videos[0])
        if not base_width or not base_height:
            base_width, base_height = 1920, 1080

        cell_width = base_width // self.cols
        cell_height = base_height // self.rows

        output_width = cell_width * self.cols
        output_height = cell_height * self.rows

        random_name = random_with_system_time()
        output_video = os.path.join(video_output_dir, f"grid-{self.layout}-{random_name}.mp4")
        usernames_file = os.path.join(video_output_dir, f"grid-{self.layout}-{random_name}.usernames")

        if usernames:
            try:
                with open(usernames_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(usernames))
                print(f"保存用户名列表: {usernames_file}")
            except Exception as e:
                print(f"保存用户名列表失败: {e}")

        scaled_videos = []
        for i, video in enumerate(selected_videos):
            username = extract_username_from_filename(video)
            scaled_video = generate_temp_filename(video, f"_scaled_{i}.mp4", work_output_dir)
            ok = self._scale_video(video, scaled_video, cell_width, cell_height, username)
            if not ok or not os.path.exists(scaled_video) or os.path.getsize(scaled_video) == 0:
                print(f"缩放失败，跳过: {video}")
            else:
                scaled_videos.append(scaled_video)

        if len(scaled_videos) < self.required_count:
            print(f"警告: 只有 {len(scaled_videos)} 个视频缩放成功，需要 {self.required_count} 个")
            for scaled in scaled_videos:
                if os.path.exists(scaled):
                    try:
                        os.remove(scaled)
                    except:
                        pass
            return None

        # 根据开关选择创建方式
        sequential_play = st.session_state.get('video_grid_sequential_play', False)
        if self.layout == '4grid':
            if sequential_play:
                final_video = self._create_4grid_sequential(scaled_videos, output_width, output_height, selected_videos)
            else:
                final_video = self._create_4grid(scaled_videos, output_width, output_height)
        else:
            final_video = self._create_9grid(scaled_videos, output_width, output_height)

        if final_video and os.path.exists(final_video) and os.path.getsize(final_video) == 0:
            print(f"错误: 宫格视频 {final_video} 为空，生成失败")
            return None

        # 清理缩放后的临时视频
        for scaled in scaled_videos:
            if os.path.exists(scaled):
                try:
                    os.remove(scaled)
                except:
                    pass

        if final_video and self.background_music and os.path.exists(self.background_music):
            final_video = self._add_background_music(final_video, self.background_music)

        return final_video, usernames_file

    def _render_username_image(self, username, output_path, width=288, font_size=24):
        """用 Pillow 把用户名渲染成白字透明底图片"""
        try:
            # 使用透明背景
            img = Image.new('RGBA', (width, font_size + 16), color=(0, 0, 0, 0))
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
            # 白字，带黑色描边
            draw.text((x, y), username, fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
            img.save(output_path)
            return True
        except Exception as e:
            print(f"渲染用户名图片失败: {e}")
            return False

    def _scale_video(self, input_video, output_video, width, height, username=None):
        """缩放视频到指定尺寸并添加用户名字幕"""
        scaled_path = generate_temp_filename(input_video, "_scaled_raw.mp4", work_output_dir)

        vf = f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}'
        command = [
            'ffmpeg', '-i', input_video,
            '-vf', vf,
            '-r', str(self.fps),
            '-c:v', 'libx264', '-preset', 'fast',
            '-y', scaled_path
        ]
        print("缩放视频:", ' '.join(command))
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"缩放视频失败: {result.stderr}")
            if os.path.exists(scaled_path):
                try:
                    os.remove(scaled_path)
                except:
                    pass
            return

        if username:
            img_path = generate_temp_filename(input_video, "_username.png", work_output_dir)
            ok = self._render_username_image(username, img_path, width=width)
            if ok:
                # 位置调整：中上部，距顶部约5%的位置
                overlay_y = height * 0.05  # 视频高度的5%位置
                overlay_cmd = [
                    'ffmpeg', '-i', scaled_path,
                    '-i', img_path,
                    '-filter_complex', f'[0:v][1:v]overlay=(W-w)/2:{int(overlay_y)}',
                    '-c:v', 'libx264', '-preset', 'fast',
                    '-y', output_video
                ]
                print("叠加字幕:", ' '.join(overlay_cmd))
                result2 = subprocess.run(overlay_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                for f in [img_path, scaled_path]:
                    try:
                        if os.path.exists(f):
                            os.remove(f)
                    except:
                        pass
                if result2.returncode != 0:
                    print(f"叠加字幕失败: {result2.stderr}")
                    return False
                return True
            else:
                try:
                    if os.path.exists(scaled_path):
                        os.rename(scaled_path, output_video)
                except:
                    pass
                return False
        else:
            try:
                if os.path.exists(scaled_path):
                    os.rename(scaled_path, output_video)
            except:
                pass
            return True

    def _create_4grid(self, scaled_videos, output_width, output_height):
        """创建4宫格视频，4个视频同时播放"""
        v1 = scaled_videos[0]
        v2 = scaled_videos[1]
        v3 = scaled_videos[2]
        v4 = scaled_videos[3]

        random_name = random_with_system_time()
        output_video = os.path.join(video_output_dir, f"grid-4grid-{random_name}.mp4")
        
        # 先获取每个视频的时长，找出最长的
        def get_duration(video):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                   '-of', 'default=noprint_wrappers=1:nokey=1', video]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            try:
                return float(result.stdout.strip())
            except:
                return 0
        
        durations = [get_duration(v) for v in [v1, v2, v3, v4]]
        max_duration = max(durations) if durations else 10
        print(f"视频时长: {durations}, 最长: {max_duration}")
        
        # 让所有视频循环到最长时长，然后合并
        filter_complex = f"""
        [0:v]trim=0:{max_duration},setpts=PTS-STARTPTS,loop=0:size=0:duration={int(max_duration)+1}[v1];
        [1:v]trim=0:{max_duration},setpts=PTS-STARTPTS,loop=0:size=0:duration={int(max_duration)+1}[v2];
        [2:v]trim=0:{max_duration},setpts=PTS-STARTPTS,loop=0:size=0:duration={int(max_duration)+1}[v3];
        [3:v]trim=0:{max_duration},setpts=PTS-STARTPTS,loop=0:size=0:duration={int(max_duration)+1}[v4];
        [v1][v2]hstack=inputs=2[top];
        [v3][v4]hstack=inputs=2[bottom];
        [top][bottom]vstack=inputs=2[out]
        """

        command = [
            'ffmpeg',
            '-i', v1,
            '-i', v2,
            '-i', v3,
            '-i', v4,
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-r', str(self.fps),
            '-c:v', 'libx264', '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            '-t', str(max_duration),
            '-y',
            output_video
        ]
        print("创建4宫格:", " ".join(command))
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            print(f"创建4宫格失败: {result.stderr}")

        return output_video if os.path.exists(output_video) else None

    def _create_4grid_sequential(self, scaled_videos, output_width, output_height, original_videos):
        """创建4宫格视频，4个视频依次播放（每个播放时其他3个静止）"""
        import uuid
        
        cell_w = output_width // 2
        cell_h = output_height // 2
        
        # 获取每个视频的时长
        def get_duration(video):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                   '-of', 'default=noprint_wrappers=1:nokey=1', video]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            try:
                return float(result.stdout.strip())
            except:
                return 10
        
        durations = [get_duration(v) for v in scaled_videos]
        print(f"依次播放：每个视频时长 {durations}, 总时长: {sum(durations):.1f}秒")
        
        # 为每个视频截取静态帧
        def get_frame(video, time_pos, output_path):
            cmd = ['ffmpeg', '-i', video, '-ss', str(time_pos), '-vframes', '1', '-y', output_path]
            subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            return output_path if os.path.exists(output_path) else video
        
        frames = []
        for i, v in enumerate(scaled_videos):
            frame_path = os.path.join(work_output_dir, f"frame_{i}_{uuid.uuid4().hex[:8]}.png")
            get_frame(v, 0.5, frame_path)
            frames.append(frame_path)
        
        # 为每个时间段创建4宫格片段（保留活动视频的音频）
        segments = []
        for seg_idx in range(4):
            active_video_idx = seg_idx
            seg_output = os.path.join(work_output_dir, f"seg_{seg_idx}_{uuid.uuid4().hex[:8]}.mp4")
            
            # 计算活动视频的 overlay 位置
            overlay_x = (active_video_idx % 2) * cell_w
            overlay_y = (active_video_idx // 2) * cell_h
            
            vf = f'scale={cell_w}:{cell_h}'
            
            filter_complex = f"""
            [0:v]{vf}[f0];
            [1:v]{vf}[f1];
            [2:v]{vf}[f2];
            [3:v]{vf}[f3];
            [f0][f1]hstack=inputs=2[top_frame];
            [f2][f3]hstack=inputs=2[bottom_frame];
            [top_frame][bottom_frame]vstack=inputs=2[bg];
            [4:v]{vf}[active];
            [bg][active]overlay={overlay_x}:{overlay_y}[out]
            """
            
            # 4个静态帧 + 1个活动视频（保留音频）
            cmd = [
                'ffmpeg',
                '-i', frames[0],
                '-i', frames[1],
                '-i', frames[2],
                '-i', frames[3],
                '-i', scaled_videos[active_video_idx],
                '-filter_complex', filter_complex,
                '-map', '[out]',
                '-map', '4:a?',  # 保留活动视频的音频
                '-t', str(durations[active_video_idx]),
                '-r', str(self.fps),
                '-c:v', 'libx264', '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-y', seg_output
            ]
            subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if os.path.exists(seg_output):
                segments.append(seg_output)
        
        if len(segments) < 4:
            print(f"创建片段失败，只有 {len(segments)} 个")
            return None
        
        # 合并所有片段（混合音频）
        concat_list = os.path.join(work_output_dir, f"concat_{uuid.uuid4().hex[:8]}.txt")
        with open(concat_list, 'w', encoding='utf-8') as f:
            for seg in segments:
                f.write(f"file '{seg}'\n")
        
        random_name = random_with_system_time()
        output_video = os.path.join(video_output_dir, f"grid-4grid-{random_name}.mp4")
        
        command = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', concat_list,
            '-c:v', 'libx264', '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-y', output_video
        ]
        print("创建4宫格(依次播放):", output_video)
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        # 清理临时文件
        for f in segments + [concat_list]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass
        for f in frames:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass
        
        if result.returncode != 0:
            print(f"创建4宫格(依次播放)失败: {result.stderr}")
            return None

        return output_video if os.path.exists(output_video) else None

    def _create_9grid(self, scaled_videos, output_width, output_height):
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

        random_name = random_with_system_time()
        output_video = os.path.join(video_output_dir, f"grid-9grid-{random_name}.mp4")

        filter_complex = f"""
        [0:v][1:v][2:v]hstack=inputs=3[row1];
        [3:v][4:v][5:v]hstack=inputs=3[row2];
        [6:v][7:v][8:v]hstack=inputs=3[row3];
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

    def _add_background_music(self, video_file, audio_file):
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
