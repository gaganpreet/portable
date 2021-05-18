from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Artist:
    name: str
    id: Optional[str] = None


@dataclass
class Album:
    name: str
    artists: Artist
    type_: str
    year: Optional[int] = None
    id: Optional[str] = None


@dataclass
class Track:
    artist: Artist
    name: str
    album: Optional[Album] = None
    id: Optional[str] = None


@dataclass
class Playlist:
    name: str
    id: str
    tracks: List[Track]
    public: bool
    description: Optional[str] = None
    count: Optional[int] = None
