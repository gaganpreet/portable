from functools import lru_cache
from typing import List
import spotipy
from fuzzywuzzy import process
from spotipy.oauth2 import SpotifyOAuth

from portable.base import MusicLibrary
from portable.schemas import Album, Artist, Playlist, Track


class SpotifyLibrary(MusicLibrary):
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
