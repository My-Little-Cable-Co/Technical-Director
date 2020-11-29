from ffmpy import FFmpeg, FFprobe
from decimal import Decimal
import subprocess
import json

def get_video_duration_in_seconds(video_information):
    chapter_info = video_information['chapters']
    if chapter_info:
        duration = Decimal(0)
        for chapter in chapter_info:
            duration += (Decimal(chapter['end_time']) - Decimal(chapter['start_time']))
    else:
        # Use the duration of the first stream with "codec_type" == "video"
        stream_info = [stream for stream in video_information['streams'] if stream['codec_type'] == 'video'][0]
        return Decimal(stream_info['duration'])
    return duration

def get_video_information(video_path):
    cmd = FFprobe(global_options='-print_format json -show_streams -show_chapters', inputs={video_path: None})
    stdout, stderr = cmd.run(stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return json.loads(stdout.decode('UTF-8').rstrip())
