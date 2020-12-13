from pprint import pprint

from portable.youtube_music import YoutubeMusicLibrary
from portable.spotify import SpotifyLibrary


def main():
    yt = YoutubeMusicLibrary()
    spotify = SpotifyLibrary()
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
