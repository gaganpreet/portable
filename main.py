from pprint import pprint

from portable.youtube_music import YoutubeMusicLibrary
from portable.spotify import SpotifyLibrary


def main():
    yt = YoutubeMusicLibrary()
    spotify = SpotifyLibrary()
    for album in yt.get_albums():
        spotify.add_album(album)
    for artist in yt.get_subscribed_artists():
        spotify.subscribe_to_artist(artist)
    for track in yt.get_liked_songs():
        spotify.like_track(track)
    for old_playlist in yt.get_playlists():
        new_playlist = spotify.create_playlist(old_playlist)
        spotify.add_tracks_to_playlist(new_playlist, old_playlist.tracks)


if __name__ == "__main__":
    main()
