from pprint import pprint
from ytmusicapi import YTMusic
from typing import List

from portable.base import MusicLibrary
from portable.schemas import Album, Artist, Playlist, Track


class YoutubeMusicLibrary(MusicLibrary):
    def __init__(self):
        self.ytmusic = YTMusic("headers_auth.json")

    def add_album(self, album: Album):
        raise NotImplementedError()

    def like_track(self, track: Track):
        raise NotImplementedError()

    def subscribe_to_artist(self, artist: Artist):
        raise NotImplementedError()

    def create_playlist(self, playlist: Playlist, tracks: List[Track]):
        raise NotImplementedError()

    def get_subscribed_artists(self):
        return [
            Artist(name=artist["artist"])
            for artist in self.ytmusic.get_library_subscriptions()
        ]

    def get_playlists(self):
        playlists = []
        for basic_playlist_data in self.ytmusic.get_library_playlists()[:2]:
            playlist_id = basic_playlist_data["playlistId"]
            playlist_data = self.ytmusic.get_playlist(playlist_id)
            public = True if playlist_data["privacy"] == "PUBLIC" else False
            pprint(playlist_data)
            playlists.append(
                Playlist(
                    name=basic_playlist_data["title"],
                    id=basic_playlist_data["playlistId"],
                    count=int(playlist_data.get("trackCount", 0)),
                    public=public,
                    description=playlist_data.get("description", None),
                    tracks=[
                        self._track_data_to_track(track_data)
                        for track_data in playlist_data["tracks"]
                    ],
                )
            )
        return playlists

    def get_liked_songs(self):
        tracks = []
        for track_data in self.ytmusic.get_liked_songs()["tracks"]:
            track = self._track_data_to_track(track_data)
            tracks.append(track)
        return tracks

    def get_albums(self):
        album_data = self.ytmusic.get_library_albums(limit=25)
        albums: List[Album] = []
        for album in album_data:
            # Can album['artists'] be a list?
            artists = Artist(album["artists"]["name"])
            albums.append(
                Album(
                    artists=artists,
                    year=album["year"],
                    name=album["title"],
                    type_=album["type"],
                )
            )
        return albums

    @staticmethod
    def _track_data_to_track(track_data) -> Track:
        artist = Artist(name=track_data["artists"][0]["name"])
        album = None
        if track_data["album"]:
            album = Album(
                name=track_data["album"]["name"],
                artists=artist,
                year=None,
                type_="Album",
            )
        return Track(album=album, artist=artist, name=track_data["title"])

    def _get_playlist_tracks(self, playlist: Playlist):
        return [
            self._track_data_to_track(track_data)
            for track_data in self.ytmusic.get_playlist(playlist.id)["tracks"]
        ]
