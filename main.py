import spotipy
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
    title: str
    artists: Artist
    year: Optional[int]
    type_: str


@dataclass
class Track:
    album: Optional[Album]
    artist: Artist
    title: str


class YoutubeMusic:
    def __init__(self):
        self.ytmusic = YTMusic("headers_auth.json")

    def get_subscribed_artists(self):
        return [
            Artist(name=artist["artist"])
            for artist in self.ytmusic.get_library_subscriptions()
        ]

    def get_liked_songs(self):
        tracks = []
        for track_data in self.ytmusic.get_liked_songs()["tracks"]:
            artist = Artist(name=track_data["artists"][0]["name"])
            album = None
            if track_data["album"]:
                album = Album(
                    title=track_data["album"]["name"],
                    artists=artist,
                    year=None,
                    type_="Album",
                )
            tracks.append(Track(album=album, artist=artist, title=track_data["title"]))
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
                    title=album["title"],
                    type_=album["type"],
                )
            )
        return albums


class Spotify:
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

    def _get_first_search_result(self, query, type):
        result = self.spotipy.search(query, type=type)
        key = f"{type}s"
        total, items = result[key]["total"], result[key]["items"]
        if total != 1:
            print(f"Found {total} results for {query}, expected 1. Using first result")
        return items[0]

    def get_albums(self):
        return self.spotipy.current_user_saved_albums()

    def add_album(self, album: Album):
        if album.type_ in ["Album", "EP"]:
            query = f'artist:"{album.artists.name}" album:"{album.title}"'
            item = self._get_first_search_result(query, "album")
            id = item["id"]
            if not self.spotipy.current_user_saved_albums_contains(albums=[id])[0]:
                print(f"Adding {album} to collection")
                self.spotipy.current_user_saved_albums_add(albums=[id])
            else:
                print(f"Not adding {album} to collection")
        else:
            print(f"Ignoring unknown type {album}")

    def like_track(self, track: Track):
        query = f'artist:"{track.artist.name}"  track:"{track.title}"'
        if track.album:
            query += f' album:"{track.album.title}"'
        item = self._get_first_search_result(query, "track")
        id = item["id"]
        if not self.spotipy.current_user_saved_tracks_contains(tracks=[id])[0]:
            self.spotipy.current_user_saved_tracks_add(tracks=[id])

    def subscribe_to_artist(self, artist: Artist):
        query = f'artist:"{artist.name}"'
        item = self._get_first_search_result(query, "artist")
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
    for track in yt.get_liked_songs()[:1]:
        pprint(spotify.like_track(track))


if __name__ == "__main__":
    main()
