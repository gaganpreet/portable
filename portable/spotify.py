from functools import lru_cache
from pprint import pprint
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

    def get_albums(self):
        return self.spotipy.current_user_saved_albums()

    def get_playlists(self) -> List[Playlist]:
        return super().get_playlists()

    def add_album(self, album: Album):
        if album.type_ in ["Album", "EP"]:
            query = f'artist:"{album.artists.name}" "{album.name}"'
            item = self._get_best_match_result(query, "album", album.name)
            id = item["id"]
            if not self.spotipy.current_user_saved_albums_contains(albums=[id])[0]:
                print(f"Adding {album} to collection")
                self.spotipy.current_user_saved_albums_add(albums=[id])
            else:
                print(f"{album.name} already exists in collection")
        else:
            print(f"Ignoring unknown type {album}")

    def like_track(self, track: Track):
        item = self._find_track(track)
        if item:
            id = item["id"]
            if not self.spotipy.current_user_saved_tracks_contains(tracks=[id])[0]:
                self.spotipy.current_user_saved_tracks_add(tracks=[id])

    def add_tracks_to_playlist(self, playlist: Playlist, tracks: List[Track]):
        for track in tracks:
            item = self._find_track(track=track)
            if item:
                track = self._track_data_to_track(item)
                if track in playlist.tracks:
                    print(
                        f"Track {track.name} already exists in {playlist.name}, skipping"
                    )
                    continue
                self.spotipy.playlist_add_items(playlist.id, items=[item["id"]])

    def create_playlist(self, playlist: Playlist) -> Playlist:
        return self._ensure_playlist_exists(playlist)

    def subscribe_to_artist(self, artist: Artist):
        query = f'artist:"{artist.name}"'
        item = self._get_best_match_result(query, "artist", artist.name)
        id = item["id"]
        if not self.spotipy.current_user_following_artists(ids=[id])[0]:
            print(f"Following {artist}")
            self.spotipy.user_follow_artists(ids=[id])

    def _get_best_match_result(self, query, type_, original_query):
        result = self.spotipy.search(query, type=type_)
        key = f"{type_}s"
        total, items = result[key]["total"], result[key]["items"]
        if total == 0:
            if (
                "'" in query
            ):  # Apostrophe sometimes doesn't return results on Spotify, removing it fixes it
                result = self.spotipy.search(query.replace("'", ""), type=type_)
                total, items = result[key]["total"], result[key]["items"]
            if total == 0:
                return
        if total >= 1:
            if not original_query:
                print(
                    f"Found {total} results for {query}, expected 1. Using first result"
                )
                return items[0]
            else:
                return process.extractOne(
                    original_query, items  # , processor=lambda item: item["name"]
                )[0]
        return items[0]

    def _find_track(self, track: Track):
        track_queries = [f'track:"{track.name}"', track.name]
        artist_queries = [f'artist:"{track.artist.name}"', ""]
        album_queries = ["", ""]
        if track.album:
            album_queries = [f'album:"{track.album.name}"', ""]

        for track_query in track_queries:
            for artist_query in artist_queries:
                for album_query in album_queries:
                    query = " ".join([track_query, artist_query, album_query])
                    item = self._get_best_match_result(query, "track", track.name)
                    if item:
                        return item
        print(f"No results for {track.name}")
        return

        query = f'{track.name} artist:"{track.artist.name}"'
        if track.album:
            query += f' album:"{track.album.name}"'
        item = self._get_best_match_result(query, "track", track.name)
        if not item:
            # Fall back queries with other combinations
            query = f'{track.name} artist:"{track.artist.name}"'
            item = self._get_best_match_result(query, "track", track.name)
            if not item and track.album:
                query += f'{track.name} album:"{track.album.name}"'
                item = self._get_best_match_result(query, "track", track.name)
            if not item:
                query = f"{track.name}"
                item = self._get_best_match_result(query, "track", track.name)
        return item

    def _ensure_playlist_exists(self, playlist: Playlist) -> Playlist:
        matched_spotify_playlist = None
        for spotify_playlist in self._get_all_spotify_playlists():
            if spotify_playlist["name"] == playlist.name:
                print(
                    f"Playlist {playlist.name} already exists, tracks will be added to this existing playlist"
                )
                matched_spotify_playlist = spotify_playlist
        if not matched_spotify_playlist:
            matched_spotify_playlist = self.spotipy.user_playlist_create(
                user=self.spotipy.me()["id"],
                name=f"{playlist.name}",
                public=playlist.public,
            )
        playlist = Playlist(
            name=matched_spotify_playlist["name"],
            id=matched_spotify_playlist["id"],
            count=matched_spotify_playlist["tracks"]["total"],
            public=matched_spotify_playlist["public"],
            tracks=self._get_playlist_tracks(matched_spotify_playlist["id"]),
        )
        return playlist

    @lru_cache(maxsize=1024)
    def _get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        tracks = []
        spotify_tracks = self.spotipy.user_playlist_tracks(
            user=self.spotipy.me()["id"], playlist_id=playlist_id, limit=100, offset=0
        )
        while spotify_tracks:
            for spotify_track in spotify_tracks["items"]:
                track = self._track_data_to_track(spotify_track["track"])
                tracks.append(track)
            if spotify_tracks["next"]:
                spotify_tracks = self.spotipy.next(spotify_tracks)
            else:
                spotify_tracks = None
        return tracks

    def _track_data_to_track(self, track_data) -> Track:
        artist = Artist(name=track_data["artists"][0]["name"])
        album = None
        if track_data["album"]:
            album_data = track_data["album"]
            album = Album(
                name=album_data["name"],
                artists=artist,
                type_=album_data["album_type"],
                year=album_data["release_date"],
                id=album_data["id"],
            )
        track = Track(
            name=track_data["name"], id=track_data["id"], artist=artist, album=album
        )
        return track

    @lru_cache(maxsize=1024)
    def _get_all_spotify_playlists(self):
        playlists = []
        spotify_playlists = self.spotipy.current_user_playlists()
        while spotify_playlists:
            playlists.extend(spotify_playlists["items"])
            if spotify_playlists["next"]:
                spotify_playlists = self.spotipy.next(playlists)
            else:
                spotify_playlists = None
        return playlists
