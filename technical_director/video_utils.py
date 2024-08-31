from decimal import Decimal
import json
from pathlib import Path
import subprocess

from ffmpy import FFmpeg, FFprobe


def get_video_duration_in_seconds(video_information) -> Decimal:
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


def get_video_information(video_path) -> dict:
    cmd = FFprobe(global_options='-print_format json -show_streams -show_chapters', inputs={video_path: None})
    stdout, stderr = cmd.run(stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return json.loads(stdout.decode('UTF-8').rstrip())


def get_default_video_filepath(channel_number=None) -> str:
    td_config_dir = Path.home().joinpath('.mylittlecableco', 'technical_director')
    default_video_file = td_config_dir / 'smpte.mp4'
    if default_video_file.exists():
        return str(default_video_file)

    # The default video doesn't exist, so we'll generate it

    # Ensure the config directory exists
    td_config_dir.mkdir(parents=True, exist_ok=True)

    video_caption = "MyLittleCableCo"
    if channel_number is not None:
        video_caption += f" Ch {channel_number}"

    # Form the ffmpeg command to generate the test file
    cmd = FFmpeg(
        inputs={None: f"-f lavfi -i smptebars=size=640x480,drawtext=text='{video_caption}':font='mono|bold':fontcolor=white:fontsize=42:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-text_w)/2:y=(h-text_h)/2 -t 1800"},
        outputs={default_video_file: None}
    )
    stdout, stderr = cmd.run(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(default_video_file)
