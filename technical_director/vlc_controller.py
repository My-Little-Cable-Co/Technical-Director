from vlc import Instance

DEFAULT_PLAYER_OPTIONS = [
    #'--fullscreen',
    '--no-osd',
    '--no-video-title-show',
    # If we reach the end of the playlist, we will pause rather than end the
    # playlist. If we keep the last video a generic "we'll be right back"
    # message, we'll pause on that while we figure out what to play next.
    #'--play-and-pause',
]

class VLCController:
    def __init__(self):
        self.vlc_instance = Instance(' '.join(DEFAULT_PLAYER_OPTIONS))
        self.media_list = self.vlc_instance.media_list_new()
        self.media_list_player = self.vlc_instance.media_list_player_new()
        self.media_list_player.get_media_player().set_fullscreen(True)
        self.media_list_player.set_media_list(self.media_list)

    def queue_video(self, video):
        self.media_list.add_media(video)

    def play(self):
        self.media_list_player.play()

    def print_queue(self):
        for i in range(0,len(self.media_list)):
            print(self.media_list.item_at_index(i).get_mrl())
