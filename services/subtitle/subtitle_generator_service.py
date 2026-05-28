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
import io
import os
import re
from dataclasses import dataclass

from config.config import my_config
from services.llm.llm_provider import get_llm_provider


@dataclass
class SubtitleSegment:
    """字幕片段数据结构"""
    index: int
    start_time: str  # 字幕时间轴开始，如 "00:00:00"
    end_time: str    # 字幕时间轴结束，如 "00:00:15"
    duration: int    # 时长（秒）
    narration: str   # 解说文案
    source_timecode: str  # 原片截取时间码，如 "00:00:00 → 00:00:15"


class SubtitleGeneratorService:
    """AI字幕生成服务"""

    def __init__(self):
        self.llm_provider = my_config['llm']['provider']
        self.llm = get_llm_provider(self.llm_provider)

    def generate_subtitle(self, movie_name: str, total_duration: int, style: str, language: str = "中文", custom_requirements: str = None) -> list:
        """根据电影名、时长、风格生成字幕片段

        Args:
            movie_name: 电影/视频名称
            total_duration: 总时长（秒）
            style: 解说风格
            language: 回复语言
            custom_requirements: 自定义剪辑要求

        Returns:
            SubtitleSegment列表
        """
        # 构建 Prompt
        prompt = self._build_prompt(movie_name, total_duration, style, language, custom_requirements)

        # 调用 LLM
        print(f"正在调用 {self.llm_provider} 生成字幕...")
        response = None
        try:
            from langchain.prompts import PromptTemplate
            prompt_template = PromptTemplate(
                input_variables=["topic", "language", "length"],
                template="{topic}"
            )
            result = self.llm.generate_content(
                topic=prompt,
                prompt_template=prompt_template,
                language=language,
                length=str(total_duration)
            )
            # 检查返回值是否是有效内容
            if result and not result.startswith("LLM调用失败") and len(result) > 50:
                response = result
            else:
                print(f"LLM返回无效内容: {result}")
        except Exception as e:
            print(f"LLM调用失败: {e}")

        # 如果 LLM 调用失败，使用备用方法
        if not response:
            response = self._fallback_generate(movie_name, total_duration, style)

        # 解析响应
        segments = self._parse_llm_response(response, total_duration)
        return segments

    def _build_prompt(self, movie_name: str, total_duration: int, style: str, language: str, custom_requirements: str = None) -> str:
        """构建生成字幕的Prompt"""
        prompt = f"""请为电影/视频《{movie_name}》生成解说字幕脚本。

要求：
1. 总时长约 {total_duration} 秒
2. 风格：{style}
3. 每个片段时长建议 15-25 秒
4. 请用{language}回复
5. 只返回CSV格式内容，不要其他解释，格式如下：
序号,字幕时间轴,时长,解说文案,原片截取时间码"""

        # 添加自定义要求
        if custom_requirements:
            prompt += f"""

用户剪辑要求：
{custom_requirements}
"""

        prompt += """

重要说明：
- 字幕时间轴是从0开始的累计时间，用于最终视频
- 原片截取时间码是你根据电影情节自己设定的合理时间点（格式：00:00:00 → 00:00:20）
- 每个片段的解说文案要写得完整具体，是真正的解说内容
- 内容要有逻辑性，像一个完整的解说视频脚本

示例格式（以电影《泰坦尼克号》为例）：
1,00:00:00 → 00:00:25,25秒,1912年4月10日，被称为"永不沉没"的泰坦尼克号从英国南安普顿港启航，载着2000多名乘客驶向大西洋彼岸的纽约。这艘当时世界上最大的豪华客轮，准备书写航海史上的传奇...,00:15:30 → 00:15:55
2,00:00:25 → 00:00:50,25秒,杰克是一个穷困潦倒的年轻画家，他在码头的赌博中赢得了三等舱的船票。正是这张船票，让他登上了这艘命运之船...,00:25:10 → 00:25:35
"""
        return prompt

    def _fallback_generate(self, movie_name: str, total_duration: int, style: str) -> str:
        """当LLM调用失败时的备用生成方法"""
        # 计算需要的片段数
        avg_duration = 20  # 平均每个片段20秒
        num_segments = max(1, total_duration // avg_duration)

        lines = ["序号,字幕时间轴,时长,解说文案,原片截取时间码"]
        current_time = 0

        # 根据风格生成不同的占位文案模板
        style_templates = {
            "感人煽情": "这段情节展现了人物之间的深厚情感，画面中{}，解说需要配合这种氛围...",
            "震撼大片": "这是一个精彩的视觉场景，画面中{}，展现了大片的震撼效果...",
            "知识科普": "这个片段介绍了重要的知识点：{}，观众可以从中了解到...",
            "悬疑紧张": "情节发展到了关键时刻，{}，观众屏住呼吸等待接下来的反转...",
            "轻松幽默": "这一段充满了欢乐的气氛，{}，让人忍俊不禁...",
            "热血激昂": "高潮部分来临，{}，激动人心的场景让观众热血沸腾...",
            "抒情文艺": "画面中{}，充满了文艺气息，解说配合着舒缓的节奏..."
        }

        scene_templates = [
            "人物站在甲板上眺望远方",
            "船只缓缓驶入港口",
            "夕阳下的城市天际线",
            "暴风雨即将来临",
            "人物在街头漫步",
            "一场激烈的对峙",
            "感人的告别场景",
            "神秘的地下通道"
        ]

        import random
        template = style_templates.get(style, style_templates["知识科普"])

        for i in range(1, num_segments + 1):
            seg_duration = min(avg_duration, total_duration - current_time)
            if seg_duration <= 0:
                break

            end_time = current_time + seg_duration
            start_hms = self._seconds_to_hhmmss(current_time)
            end_hms = self._seconds_to_hhmmss(end_time)

            # 估算原片时间（假设原片总长约2小时，随机位置）
            source_offset = random.randint(0, 6000)  # 0-100分钟
            source_start = self._seconds_to_hhmmss(source_offset)
            source_end = self._seconds_to_hhmmss(source_offset + seg_duration)

            # 生成更有意义的占位文案
            scene = random.choice(scene_templates)
            narration = f"《{movie_name}》第{i}段解说：{template.format(scene)} 建议配合相应画面进行剪辑..."

            lines.append(f"{i},{start_hms} → {end_hms},{seg_duration}秒,{narration},{source_start} → {source_end}")

            current_time = end_time

        return "\n".join(lines)

    def _parse_llm_response(self, response: str, total_duration: int) -> list:
        """解析LLM返回的CSV响应"""
        segments = []

        # 尝试提取CSV内容
        csv_content = self._extract_csv(response)
        if not csv_content:
            print("无法解析LLM响应，使用备用方法")
            return self._fallback_parse(total_duration)

        # 解析CSV
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        # 跳过标题行
        for row in rows:
            if len(row) < 5 or row[0].isdigit() is False:
                # 检查是否是标题行
                if '序号' in row[0] or 'index' in row[0].lower():
                    continue
                continue

            try:
                index = int(row[0].strip())
                timeline = row[1].strip()
                duration_str = row[2].strip()
                narration = row[3].strip()
                source_timecode = row[4].strip()

                # 解析时长
                duration = self._parse_duration(duration_str)

                # 解析时间轴
                start_time, end_time = self._parse_timeline(timeline)

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

        # 如果解析失败，使用备用方法
        if not segments:
            return self._fallback_parse(total_duration)

        return segments

    def _extract_csv(self, text: str) -> str:
        """从文本中提取CSV内容"""
        # 移除 markdown 代码块
        text = re.sub(r'```csv\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

        # 查找CSV开始位置
        lines = text.split('\n')
        start_idx = 0
        for i, line in enumerate(lines):
            if re.match(r'^\d+', line.strip()):
                start_idx = i
                break

        return '\n'.join(lines[start_idx:])

    def _parse_duration(self, duration_str: str) -> int:
        """解析时长字符串"""
        # 移除"秒"字
        duration_str = duration_str.replace('秒', '').strip()
        try:
            return int(float(duration_str))
        except:
            return 20  # 默认20秒

    def _parse_timeline(self, timeline: str) -> tuple:
        """解析字幕时间轴"""
        parts = timeline.split('→')
        if len(parts) != 2:
            parts = timeline.split('->')
        if len(parts) != 2:
            parts = timeline.split('-')

        if len(parts) == 2:
            start = parts[0].strip()
            end = parts[1].strip()
            return start, end

        return "", ""

    def _seconds_to_hhmmss(self, seconds: int) -> str:
        """将秒数转换为 HH:MM:SS 格式"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _fallback_parse(self, total_duration: int) -> list:
        """备用解析方法"""
        segments = []
        avg_duration = 20
        num_segments = max(1, total_duration // avg_duration)
        current_time = 0

        for i in range(1, num_segments + 1):
            duration = min(avg_duration, total_duration - current_time)
            if duration <= 0:
                break

            end_time = current_time + duration

            # 估算原片时间
            import random
            source_offset = random.randint(0, 6000)

            segment = SubtitleSegment(
                index=i,
                start_time=self._seconds_to_hhmmss(current_time),
                end_time=self._seconds_to_hhmmss(end_time),
                duration=duration,
                narration=f"这是第{i}段的解说文案，请根据电影情节修改...",
                source_timecode=f"{self._seconds_to_hhmmss(source_offset)} → {self._seconds_to_hhmmss(source_offset + duration)}"
            )
            segments.append(segment)
            current_time = end_time

        return segments

    def export_to_csv(self, segments: list, output_path: str) -> str:
        """导出字幕为CSV文件

        Args:
            segments: SubtitleSegment列表
            output_path: 输出文件路径

        Returns:
            输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['序号', '字幕时间轴', '时长', '对应解说文案', '电影原片截取时间码'])

            for seg in segments:
                writer.writerow([
                    seg.index,
                    f"{seg.start_time} → {seg.end_time}",
                    f"{seg.duration}秒",
                    seg.narration,
                    seg.source_timecode
                ])

        print(f"字幕已导出到: {output_path}")
        return output_path


def create_subtitle_generator_service() -> SubtitleGeneratorService:
    """创建字幕生成服务的便捷函数"""
    return SubtitleGeneratorService()
