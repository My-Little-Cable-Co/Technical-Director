import time
import datetime
import pyautogui
import random
from decimal import Decimal

from vlc import EventType
from vlc_controller import VLCController
from video import Video

from commercial_utils import get_commercial_break

class TechnicalDirector:
    def __init__(self):
        self.vlc_controller = VLCController()

        # This is the semephore we look for to know if we should advance the
        # queue. When VLC sends the event that represents the player reaching
        # the end of the currently-playing media, we set this to True, which
        # we then react to in the endless loop.
        self.should_move_to_next_video = False

        self.current_video_started = None
        self.current_video_duration_in_seconds = None
        self.video_queue = []
        self.feed_queue()

    def feed_queue(self, time_at_queue_completion=datetime.datetime.now()):
        scheduling_block = self.get_scheduling_block(time_at_queue_completion)

        # Get a Video object for the video that should be airing.
        target_video = Video(scheduling_block['target_video'])

        # See how much time is left in the programming block.
        # Example:
        # We are in the middle of a 30 minute block.
        # It started 27 minutes, 30 seconds ago.
        # We have 2 minutes, thirty seconds left.
        remaining_time = self.seconds_until_end_of_scheduling_block(scheduling_block)

        # If the remaining time is less than the duration of the target video,
        # queue it so that it ends at the cutover.
        video_duration = target_video.duration_in_seconds()
        if remaining_time < video_duration:
            print('Not enough time to show the whole thing!')
            print(f'There are {remaining_time} seconds left, but the video is {video_duration} seconds long!')
            self.queue_video(target_video,
                start_at_second=(video_duration-remaining_time),
                intersperse_commercials=False,
                block_duration_in_seconds=scheduling_block['block_duration_in_minutes'] * 60)
        # Else queue it and pad with commercials.
        else:
            print('There is enough time to show the whole thing.')
            print(f'There are {remaining_time} seconds left, and the video is {video_duration} seconds long.')
            self.queue_video(target_video,
                intersperse_commercials=scheduling_block['show_commercials'],
                block_duration_in_seconds=scheduling_block['block_duration_in_minutes'] * 60)
        self.print_queue()

    def react_to_vlc_media_player_end_reached_event(self, event):
        # Hey there. The reason this just sets a flag and doesn't just start
        # the next video itself is because attempting to call methods on the
        # player object while reacting to a player event causes the player to
        # hang. Instead this just sets a semephore that is read during the main
        # loop.
        self.should_move_to_next_video = True

    def play_next_video(self):
        # TODO: Future: except IndexError (no videos queued) and show a
        # "we'll be right back" image/video.
        video = self.video_queue.pop(0)
        media = self.vlc_controller.vlc_instance.media_new(video.file_path)
        # If start_at_second is specified, we don't bother with chapters,
        # commercials, etc. Just queue the video from the time specified.
        # This usually occurs when there is not enough time in the timeslot
        # to show the entire video. Sounds like it should never happen, right?
        # Well, it can happen if you turn your channel on in the middle of a
        # timeslot. In this case it would be like the content had been playing,
        # it finishes exactly on time.
        if video.start_at_second:
            media.add_option(f':start-time={round(Decimal(video.start_at_second), 3)}')
        if video.end_at_second:
            media.add_option(f":stop-time={round(Decimal(video.end_at_second), 3)}")

        self.vlc_controller.set_media(media)

        self.vlc_controller.play()
        self.current_video_started = datetime.datetime.now()
        self.current_video_duration_in_seconds = video.duration_in_seconds()

    def queue_video(self, target_video, start_at_second=0, intersperse_commercials=False, block_duration_in_seconds=(30 * 60)):
        if start_at_second:
            # If start_at_second is specified, we don't bother with chapters,
            # commercials, etc. Just queue the video from the time specified.
            target_video.start_at_second = start_at_second
            self.video_queue.append(target_video)
        else:
            # In this logic branch, we will queue the video, but we will
            # potentially prepend, append, and intersperse commercials.
            # The end result is more videos than the target video gets queued,
            # and the target video might get queued several times, once for
            # each segment.
            #
            # Example:
            # 1. Start off with commercials, queue three commercial videos
            # 2. Queue the video from the beginning until the first commercial break
            # 3. Queue two more commercial videos
            # 4. Queue the video from where we left off in step 2 until the end
            # 5. Play three more commercials.
            #
            # In this example, we queued 10 videos total, including the target
            # video twice.

            videos_to_queue = []

            # Figure out how many commercial breaks we'll have. We could have
            # one before we start the video, we could have one after we end the
            # video, and we might decide to put commercials within the video at
            # the chapter markers.
            commercials_before_start = random.randint(0,1) == 1
            commercials_after_end = random.randint(0,1) == 1
            total_commercial_breaks = 0
            if commercials_before_start:
                total_commercial_breaks += 1
            if commercials_after_end:
                total_commercial_breaks += 1
            if intersperse_commercials:
                total_commercial_breaks += max(len(target_video.chapters()) - 1, 0)

            # Ensure there is at least one commercial break. There is the chance
            # that the video does not contain chapter information, and both the
            # random chances decided that there would be no starting and no
            # ending commercials. In this case, we would almost certainly have
            # dead air (nothing playing), since the video content tends to be
            # a shorter duration than the programming block it is being played
            # in. (An episode plays in a 30 minute block, but the episode is
            # intentionally less than 30 minutes to allow for commercials.)
            total_commercial_breaks = max(total_commercial_breaks, 1)

            # Figure out how long the target video is
            content_duration_in_seconds = target_video.duration_in_seconds()

            # Figure out how much time is leftover in the block
            # Example: A 24 minute episode airing in a 30 minute long
            # programming block has 6 minutes leftover.
            block_duration_minus_content_duration_in_seconds = block_duration_in_seconds - content_duration_in_seconds

            # Knowing how much time you need to fill, and how many breaks you
            # have to fill it, get a list of commercial file paths, grouped by
            # which break to show them in.
            commercial_breaks = self.assemble_commercial_breaks(total_commercial_breaks, block_duration_minus_content_duration_in_seconds)

            if commercials_before_start:
                # If we are supposed to have a commercial break before the
                # content begins, grab one of our prepared commercial breaks,
                # create Video objects from each of the file paths, and append
                # them to the video queue.
                commercial_break = commercial_breaks.pop()
                for commercial_file_path in commercial_break:
                    self.video_queue.append(Video(commercial_file_path, batch_label=target_video.batch_label))
            if target_video.chapters() and intersperse_commercials:
                # Since this video has chapters and we've elected to insert
                # commercials, lets go through each chapter, queue it, then
                # queue a commercial break after it. Unless it's the last
                # chapter. When we don't add a commercial break after that one
                # here. We handle that further down based on the value of
                # `commercials_after_end`.
                for index, chapter in enumerate(target_video.chapters()):
                    video_segment = Video(target_video.file_path, batch_label=target_video.batch_label)
                    video_segment.start_at_second = round(Decimal(chapter['start_time']), 3)
                    video_segment.end_at_second = round(Decimal(chapter['end_time']), 3)
                    self.video_queue.append(video_segment)
                    if index < len(target_video.chapters()) - 1:
                        commercial_break = commercial_breaks.pop()
                        for commercial_file_path in commercial_break:
                            self.video_queue.append(Video(commercial_file_path, batch_label=target_video.batch_label))
            else:
                # Either this video did not have chapter information or we
                # elected to not insert commercials. In this case, simply queue
                # the video.
                self.video_queue.append(target_video)
            if commercials_after_end:
                # If we are supposed to have a commercial break after the
                # content ends, grab one of our prepared commercial breaks,
                # create Video objects from each of the file paths, and append
                # them to the video queue.
                commercial_break = commercial_breaks.pop()
                for commercial_file_path in commercial_break:
                    self.video_queue.append(Video(commercial_file_path, batch_label=target_video.batch_label))

    def assemble_commercial_breaks(self, count, total_length):
        commercial_breaks = []
        # TODO: make these not so even! Varying length breaks keep it fresh.
        target_length = total_length / count
        for i in range(0, count):
            commercial_breaks.append(get_commercial_break(target_length))
        return commercial_breaks
        
    def seconds_until_end_of_scheduling_block(self, scheduling_block) -> int:
        block_start = scheduling_block['block_start']
        block_duration_in_minutes = scheduling_block['block_duration_in_minutes']
        return ((block_start + datetime.timedelta(minutes=block_duration_in_minutes)) - max(datetime.datetime.now(), block_start)).seconds

    # This is just for testing purposes. The real scheduling block information
    # will come from the program guide/scheduling application.
    def get_scheduling_block(self, datetime_for_consideration):
        return {
            'target_video': '/home/pi/video/test_video/Season 01/test_video.S01.E01.mp4' if datetime_for_consideration.minute >= 30 else '/home/pi/video/test_video/Season 01/test_video.S01.E02.mp4',
            'show_commercials': True,
            'block_duration_in_minutes': 30,
            'block_start': self.most_recent_half_hour(datetime_for_consideration)
        }

    # Adapted from the logic found here: https://stackoverflow.com/a/10854034
    def most_recent_half_hour(self, datetime_for_consideration):
        thirty_minutes_in_seconds = (60 * 30)
        seconds = (datetime_for_consideration.replace(tzinfo=None) - datetime_for_consideration.min).seconds
        rounding = seconds // thirty_minutes_in_seconds * thirty_minutes_in_seconds
        return datetime_for_consideration + datetime.timedelta(0, rounding - seconds, -datetime_for_consideration.microsecond)

    # Simply sum the durations of all the videos in the video queue.
    def remaining_queue_duration_in_seconds(self):
        duration = 0
        for video in self.video_queue:
            duration += video.duration_in_seconds()
        return duration

    def estimated_time_at_end_of_current_video(self):
        if not (self.current_video_started and self.current_video_duration_in_seconds):
            return datetime.datetime.now()
        else:
            video_duration_seconds = int(self.current_video_duration_in_seconds)
            video_duration_milliseconds = int((self.current_video_duration_in_seconds - video_duration_seconds) * 1000)
            return self.current_video_started + datetime.timedelta(seconds=video_duration_seconds, milliseconds=video_duration_milliseconds)

    def print_queue(self):
        remaining_queue_duration = self.remaining_queue_duration_in_seconds()
        print(f'Queue depth is {remaining_queue_duration / 60} minutes.')
        estimated_airtime = self.estimated_time_at_end_of_current_video()

        print('current queue:')
        for index, video in enumerate(self.video_queue):
            video_duration_seconds = int(video.duration_in_seconds())
            video_duration_milliseconds = int((video.duration_in_seconds() - video_duration_seconds) * 1000)
            estimated_airtime = estimated_airtime + datetime.timedelta(seconds=video_duration_seconds, milliseconds=video_duration_milliseconds)
            print(f"[{video.batch_label}] <{estimated_airtime}> {video.file_path.split('/')[-1]} ({round(Decimal(video.duration_in_seconds()), 3)}s)")


    def queue_fill_advance_and_sleep_loop(self):
        while True:
            remaining_queue_duration = self.remaining_queue_duration_in_seconds()
            if remaining_queue_duration < (30 * 60):
                # The queue has less than thirty minutes of content lined up.
                # We'll feed the queue with what should be on at the time it
                # would be empty. (If the queue has 20 minutes in it, we'll
                # fill it with what should be on 20 minutes from now)
                queue_feed_time = self.estimated_time_at_end_of_current_video()
                remaining_seconds = int(remaining_queue_duration)
                remaining_milliseconds = int((remaining_queue_duration - remaining_seconds) * 1000)
                self.feed_queue(queue_feed_time + datetime.timedelta(seconds=remaining_seconds, milliseconds=remaining_milliseconds))

            # Advance the queue if it's ready.
            if self.should_move_to_next_video:
                self.should_move_to_next_video = False
                self.play_next_video()

            time.sleep(0.5)

# Hide the mouse cursor so it is not visible if the desktop is shown.
# Unfortunately, the desktop makes an appearance between videos. We mitigate
# the effects of this by hiding the task bar, making the background a solid
# black, and moving the mouse out of view.
pyautogui.FAILSAFE = False
pyautogui.moveTo(pyautogui.size())

# Create our TechnicalDirector instance
td = TechnicalDirector()

# Attach an event listener to the VLC player so that we can play the next video
# as soon as VLC reports that the in progress one has finished.
events = td.vlc_controller.player.event_manager()
events.event_attach(EventType.MediaPlayerEndReached, td.react_to_vlc_media_player_end_reached_event)

# Hit play
td.play_next_video()

# Endlessly add scheduled items to the queue and sleep long enough to let them
# play.
td.queue_fill_advance_and_sleep_loop()
