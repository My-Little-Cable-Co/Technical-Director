import uuid
from video_utils import (
    get_video_information,
    get_video_duration_in_seconds,
)


class Video:
    def __init__(self, file_path, batch_label=uuid.uuid4()):
        self.file_path = file_path
        self._start_at_second = None
        self._end_at_second = None
        # batch_label is used for debugging purposes. Use it to remember what
        # videos were queued as part of the same process.
        self.batch_label = str(batch_label)
        self.initialize_caches()

    def duration_in_seconds(self):
        if self._duration_in_seconds:
            # We've already calculated, no need to do it again
            return self._duration_in_seconds
        if self.start_at_second and self.end_at_second:
            # We specify start and end, the duration is the end time minus the start.
            self._duration_in_seconds = (self.end_at_second - self.start_at_second)
        elif self.start_at_second:
            # We only specify the start, so we subtract the start time from the total duration.
            whole_video_duration = get_video_duration_in_seconds(self.video_information())
            self._duration_in_seconds = (whole_video_duration - self.start_at_second)
        elif self.end_at_second:
            # We only specify the end, so the end second is the duration!
            self._duration_in_seconds = self.end_at_second
        else:
            # We do not specify a start or an end, so we play the whole video.
            self._duration_in_seconds = get_video_duration_in_seconds(self.video_information())
        return self._duration_in_seconds

    def video_information(self):
        if self._video_information:
            return self._video_information
        self._video_information = get_video_information(self.file_path)
        return self._video_information

    def chapters(self):
        return self.video_information().get('chapters', [])

    def initialize_caches(self):
        self._duration_in_seconds = None
        self._video_information = None

    @property
    def start_at_second(self):
        return self._start_at_second

    @start_at_second.setter
    def start_at_second(self, new_value):
        self.initialize_caches()
        self._start_at_second = new_value

    @property
    def end_at_second(self):
        return self._end_at_second

    @end_at_second.setter
    def end_at_second(self, new_value):
        self.initialize_caches()
        self._end_at_second = new_value
