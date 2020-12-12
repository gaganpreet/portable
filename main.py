from abc import ABC, abstractmethod
import spotipy
from fuzzywuzzy import process
from functools import lru_cache
from spotipy.oauth2 import SpotifyOAuth
from dataclasses import dataclass
from pprint import pprint
from typing import List, Optional
from ytmusicapi import YTMusic


@dataclass
class Artist:
    name: str


@dataclass
class Album:
    name: str
    artists: Artist
    type_: str
    year: Optional[int] = None


@dataclass
class Track:
    artist: Artist
    name: str
    album: Optional[Album] = None


@dataclass
class Playlist:
    name: str
    id: str
    tracks: List[Track]
    public: bool
    description: Optional[str] = None
    count: Optional[int] = None


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
        ...

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
    def create_playlist(self, playlist: Playlist, tracks: List[Track]):
        pass


class YoutubeMusic(MusicLibrary):
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


class Spotify(MusicLibrary):
    scopes = ",".join(
        [
            "playlist-read-private",
            "playlist-modify-private",
            "playlist-modify-public",
            "user-library-read",
            "user-library-modify",
            "user-follow-read",
            "user-follow-modify",
        ]
    )

    def __init__(self):
        self.spotipy = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                scope=self.scopes, redirect_uri="http://localhost:54321"
            )
        )

    def get_subscribed_artists(self) -> List[Artist]:
        raise NotImplementedError()

    def get_liked_songs(self) -> List[Track]:
        raise NotImplementedError()

    def _get_best_match_result(self, query, type_, original_query):
        result = self.spotipy.search(query, type_=type_)
        key = f"{type_}s"
        total, items = result[key]["total"], result[key]["items"]
        if total != 1:
            if not original_query:
                print(
                    f"Found {total} results for {query}, expected 1. Using first result"
                )
                return items[0]
            else:
                return process.extractOne(
                    original_query, items, processor=lambda item: item.name
                )
        return items[0]

    def get_albums(self):
        return self.spotipy.current_user_saved_albums()

    def add_album(self, album: Album):
        if album.type_ in ["Album", "EP"]:
            query = f'artist:"{album.artists.name}" album:"{album.name}"'
            item = self._get_best_match_result(query, "album", album.name)
            id = item["id"]
            if not self.spotipy.current_user_saved_albums_contains(albums=[id])[0]:
                print(f"Adding {album} to collection")
                self.spotipy.current_user_saved_albums_add(albums=[id])
            else:
                print(f"Not adding {album} to collection")
        else:
            print(f"Ignoring unknown type {album}")

    def like_track(self, track: Track):
        item = self._find_track(track)
        id = item["id"]
        if not self.spotipy.current_user_saved_tracks_contains(tracks=[id])[0]:
            self.spotipy.current_user_saved_tracks_add(tracks=[id])

    @lru_cache
    def get_playlists(self):
        offset = 0
        limit = 50
        playlists, has_more = self._get_playlist_from_offset(offset, limit)
        while has_more is True:
            offset += limit
            next_set_playlists, has_more = self._get_playlist_from_offset(offset, limit)
            playlists.extend(next_set_playlists)
        return playlists

    def _get_playlist_from_offset(self, offset: int, limit: int):
        playlists = self.spotipy.current_user_playlists(limit=limit, offset=offset)
        print(playlists["total"], offset + limit)
        return playlists["items"], playlists["total"] > offset + limit

    def _find_track(self, track: Track):
        query = f'artist:"{track.artist.name}"  track:"{track.name}"'
        if track.album:
            query += f' album:"{track.album.name}"'
        item = self._get_best_match_result(query, "track", track.name)
        return item

    def ensure_playlist_exists(self, playlist: Playlist) -> Playlist:
        print(
            self.spotipy.user_playlist_create(
                user=self.spotipy.me()["id"], name=f"{playlist.name} - Import"
            )
        )

    def add_tracks(self, playlist: Playlist, tracks: List[Track]):
        ...

    def create_playlist(self, playlist: Playlist, tracks: List[Track]):
        created_playlist = self.ensure_playlist_exists(playlist)
        self.add_tracks(created_playlist, tracks)

    def subscribe_to_artist(self, artist: Artist):
        query = f'artist:"{artist.name}"'
        item = self._get_best_match_result(query, "artist", artist.name)
        id = item["id"]
        if not self.spotipy.current_user_following_artists(ids=[id])[0]:
            print(f"Following {artist}")
            self.spotipy.user_follow_artists(ids=[id])


def main():
    yt = YoutubeMusic()
    spotify = Spotify()
    # for album in yt.get_albums()[:5]:
    #    spotify.add_album(album)
    # for artist in yt.get_subscribed_artists():
    #    spotify.subscribe_to_artist(artist)
    # for track in yt.get_liked_songs()[:1]:
    #   pprint(spotify.like_track(track))
    for playlist in yt.get_playlists()[:2]:
        pprint(spotify.get_playlists())


if __name__ == "__main__":
    main()
