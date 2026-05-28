# 测试 gen_filter 音频滤镜生成
import sys
sys.path.insert(0, '.')

from services.video.texiao_service import gen_filter

# 测试用例 (4个视频)
segments = [9.009002, 9.05, 8.6, 7.3]
transition_type = "xfade"
transition_value = "fade"
transition_duration = 1.0

print("测试: 带音频")
filter_str = gen_filter(segments, None, None, transition_type, transition_value, transition_duration, True)
print(f"滤镜字符串:")
print(filter_str)
print()
print("检查各部分:")
# 视频部分
video_parts = filter_str.split(";")
for p in video_parts:
    if 'xfade' in p:
        print(f"  视频转场: {p}")
    elif 'acrossfade' in p:
        print(f"  音频转场: {p}")
    elif 'format=yuv420p' in p:
        print(f"  视频格式化: {p}")
