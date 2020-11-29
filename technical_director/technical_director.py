import time
import datetime
import random
from decimal import Decimal

from vlc_controller import VLCController
from video_utils import (
    get_video_information,
    get_video_duration_in_seconds,
)

from commercial_utils import get_commercial_break

class TechnicalDirector:
    def __init__(self):
        self.player = VLCController()
        self.feed_queue(initializing=True)

    def feed_queue(self, initializing=False):
        # If we are initializing, fetch info on what should be currently playing.
        if initializing:
            # Get information about the current scheduling block.
            scheduling_block = self.get_current_scheduling_block()
        else:
            scheduling_block = self.get_next_scheduling_block()

        # Get information about the video that should be airing.
        video_information = get_video_information(scheduling_block['target_video'])

        # See how much time is left in the programming block.
        # Example:
        # We are in the middle of a 30 minute block.
        # It started 27 minutes, 30 seconds ago.
        # We have 2 minutes, thirty seconds left.
        remaining_time = self.seconds_until_end_of_scheduling_block(scheduling_block)

        # If the remaining time is less than the duration of the target video,
        # queue it so that it ends at the cutover.
        video_duration = get_video_duration_in_seconds(video_information)
        if remaining_time < video_duration:
            print('Not enough time to show the whole thing!')
            print(f'There are {remaining_time} seconds left, but the video is {video_duration} seconds long!')
            self.queue_video(scheduling_block['target_video'],
                video_information,
                start_at_second=(video_duration-remaining_time),
                intersperse_commercials=False,
                block_duration_in_seconds=scheduling_block['block_duration_in_minutes'] * 60)
        # Else queue it and pad with commercials.
        else:
            print('There is enough time to show the whole thing.')
            print(f'There are {remaining_time} seconds left, and the video is {video_duration} seconds long.')
            self.queue_video(scheduling_block['target_video'],
                video_information,
                intersperse_commercials=scheduling_block['show_commercials'],
                block_duration_in_seconds=scheduling_block['block_duration_in_minutes'] * 60)

    def queue_video(self, file_path, video_information, start_at_second=0, intersperse_commercials=False, block_duration_in_seconds=(30 * 60)):
        # If start_at_second is specified, we don't bother with chapters,
        # commercials, etc. Just queue the video from the time specified.
        if start_at_second:
            media = self.player.vlc_instance.media_new(file_path)
            media.add_option(f':start-time={round(start_at_second, 3)}')
            self.player.queue_video(media)
        else:
            media_to_queue = []
            commercials_before_start = random.randint(0,1) == 1
            commercials_after_end = random.randint(0,1) == 1
            total_commercial_breaks = 0
            if commercials_before_start:
                total_commercial_breaks += 1
            if commercials_after_end:
                total_commercial_breaks += 1
            if intersperse_commercials:
                total_commercial_breaks += max(len(video_information['chapters']) - 1, 0)

            content_duration_in_seconds = get_video_duration_in_seconds(video_information)
            block_duration_minus_content_duration_in_seconds = block_duration_in_seconds - content_duration_in_seconds
            commercial_breaks = self.assemble_commercial_breaks(total_commercial_breaks, block_duration_minus_content_duration_in_seconds)

            if commercials_before_start:
                commercial_break = commercial_breaks.pop()
                for commercial_file_path in commercial_break:
                    media_to_queue.append(self.player.vlc_instance.media_new(commercial_file_path))
            if video_information['chapters'] and intersperse_commercials:
                for index, chapter in enumerate(video_information['chapters']):
                    media = self.player.vlc_instance.media_new(file_path)
                    media.add_option(f":start-time={round(Decimal(chapter['start_time']), 3)}")
                    print(f"start-time={round(Decimal(chapter['start_time']), 3)}")
                    media.add_option(f":stop-time={round(Decimal(chapter['end_time']), 3)}")
                    print(f"end-time={round(Decimal(chapter['end_time']), 3)}")
                    media_to_queue.append(media)
                    if index < len(video_information['chapters']) - 1:
                        commercial_break = commercial_breaks.pop()
                        for commercial_file_path in commercial_break:
                            media_to_queue.append(self.player.vlc_instance.media_new(commercial_file_path))
            else:
                media_to_queue.append(self.player.vlc_instance.media_new(file_path))
            if commercials_after_end:
                commercial_break = commercial_breaks.pop()
                for commercial_file_path in commercial_break:
                    media_to_queue.append(self.player.vlc_instance.media_new(commercial_file_path))
            for media in media_to_queue:
                self.player.queue_video(media)

    def assemble_commercial_breaks(self, count, total_length):
        commercial_breaks = []
        # TODO: make these not so even! Varying length breaks keep it fresh.
        target_length = total_length / count
        for i in range(0, count):
            commercial_breaks.append(get_commercial_break(target_length))
        return commercial_breaks
        
    def seconds_until_end_of_scheduling_block(self, scheduling_block) -> int:
        block_started = scheduling_block['block_started']
        block_duration_in_minutes = scheduling_block['block_duration_in_minutes']
        return ((block_started + datetime.timedelta(minutes=block_duration_in_minutes)) - max(datetime.datetime.now(), block_started)).seconds

    def get_current_scheduling_block(self):
        return {
            'target_video': '/home/pi/video/test_video/Season 01/test_video.S01.E01.mp4' if datetime.datetime.now().minute >= 30 else '/home/pi/video/test_video/Season 01/test_video.S01.E02.mp4',
            'show_commercials': True,
            'block_duration_in_minutes': 30,
            'block_started': self.most_recent_half_hour()
        }

    def get_next_scheduling_block(self):
        return {
            'target_video': '/home/pi/video/test_video/Season 01/test_video.S01.E02.mp4' if datetime.datetime.now().minute >= 30 else '/home/pi/video/test_video/Season 01/test_video.S01.E01.mp4',
            'show_commercials': True,
            'block_duration_in_minutes': 30,
            'block_started': self.most_recent_half_hour()
        }

    # Adapted from the logic found here: https://stackoverflow.com/a/10854034
    def most_recent_half_hour(self):
        thirty_minutes_in_seconds = (60 * 30)
        current_time = datetime.datetime.now()
        seconds = (current_time.replace(tzinfo=None) - current_time.min).seconds
        rounding = seconds // thirty_minutes_in_seconds * thirty_minutes_in_seconds
        return current_time + datetime.timedelta(0, rounding - seconds, -current_time.microsecond)

    def next_half_hour(self):
        thirty_minutes_in_seconds = (60 * 30)
        current_time = datetime.datetime.now()
        seconds = (current_time.replace(tzinfo=None) - current_time.min).seconds
        rounding = (seconds + current_time.microsecond / 1000000 + thirty_minutes_in_seconds) // thirty_minutes_in_seconds * thirty_minutes_in_seconds
        return current_time + datetime.timedelta(0, rounding - seconds, -current_time.microsecond)

    def remaining_queue_duration_in_seconds(self):
        return 6

    def queue_and_sleep_loop(self):
        while True:
            if self.remaining_queue_duration_in_seconds() > 5:
                time.sleep(5)
            else:
                self.feed_queue()


td = TechnicalDirector()
td.player.print_queue()
td.player.play()
td.queue_and_sleep_loop()
