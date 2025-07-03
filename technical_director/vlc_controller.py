import datetime
from vlc import Instance

DEFAULT_PLAYER_OPTIONS = [
    '--no-osd',
    '--no-video-title-show',
]

class VLCController:
    def __init__(self):
        self.vlc_instance = Instance(' '.join(DEFAULT_PLAYER_OPTIONS))
        self.player = self.vlc_instance.media_player_new()
        self.player.set_fullscreen(True)

    def play(self):
        self.player.play()

    def set_media(self, media):
        self.player.set_media(media)
