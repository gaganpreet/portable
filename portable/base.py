from abc import ABC, abstractmethod
from typing import List
from portable.schemas import Artist, Track, Album, Playlist


class MusicLibrary(ABC):
    @abstractmethod
    def get_subscribed_artists(self) -> List[Artist]:
        pass

    @abstractmethod
    def get_playlists(self) -> List[Playlist]:
        pass

    @abstractmethod
    def get_liked_songs(self) -> List[Track]:
        pass

    @abstractmethod
    def get_albums(self) -> List[Album]:
        pass

    @abstractmethod
    def add_album(self, album: Album):
        pass

    @abstractmethod
    def like_track(self, track: Track):
        pass

    @abstractmethod
    def subscribe_to_artist(self, artist: Artist):
        pass

    @abstractmethod
    def create_playlist(self, playlist: Playlist):
        pass
