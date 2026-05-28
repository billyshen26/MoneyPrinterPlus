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

import streamlit as st

def gen_filter(segments, target_width, target_height,transition_type, transition_value, transition_duration ,with_audio=False):
    video_fades = ""
    audio_fades = ""
    settb = ""
    last_fade_output = "0:v"
    last_audio_output = "0:a"

    video_length = 0
    file_lengths = [0] * len(segments)

    # 确保所有 segments 都是可计算的数值类型
    segments = [float(s) for s in segments]

    if target_width:
        for i in range(len(segments)):
            settb += "[%d:v]settb=AVTB,scale=w=%d:h=%d:force_original_aspect_ratio=1,pad=%d:%d:(ow-iw)/2:(oh-ih)/2[%dv];" % (
            i, target_width, target_height, target_width, target_height, i)
    else:
        for i in range(len(segments)):
            settb += f"[{i}:v]format=yuv420p[{i}v];"

    str_list = [str(f) for f in segments]
    print("转场视频长度：" + " ".join(str_list))
    
    # 重新初始化 last_fade_output 为第一个视频的转换后标签
    last_fade_output = "0v"
    
    for i in range(len(segments) - 1):
        file_lengths[i] = segments[i]

        video_length += float(file_lengths[i])
        next_fade_output = f"v{i}{i+1}"
        # offset 是转场开始的时刻 = 到目前为止的总时长 - 转场时长
        offset = video_length - float(transition_duration)
        video_fades += f"[{last_fade_output}][{i + 1}v]{transition_type}=transition={transition_value}:duration={float(transition_duration)}:offset={offset}"
        # 最后一次转场输出到 [video]，中间转场输出到中间标签
        if i == len(segments) - 2:
            video_fades += "[video];"
        else:
            video_fades += f"[{next_fade_output}];"
        last_fade_output = next_fade_output

        if with_audio:
            next_audio_output = f"a{i}{i+1}"
            audio_fades += "[%s][%d:a]acrossfade=d=%f:c2=nofade%s" % \
                           (last_audio_output, i + 1, float(transition_duration),
                            '[' + next_audio_output + '];' if (i) < len(segments) - 2 else "[audio]")
            last_audio_output = next_audio_output

    if with_audio:
        return settb + video_fades + audio_fades
    return settb + video_fades
