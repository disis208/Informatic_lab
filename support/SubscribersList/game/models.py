from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    id: int
    login: str
    password_hash: str
    gender: Optional[str] = None
    birth_year: Optional[int] = None
    email: Optional[str] = None


@dataclass
class Worker:
    id: int
    login: str
    password_hash: str


@dataclass
class Publication:
    id: int
    title: str
    author_id: int
    tag_names: list = field(default_factory=list)
    file_path: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Tag:
    id: int
    value: str


@dataclass
class Like:
    id: int
    publication_id: int
    user_id: int


@dataclass
class Subscription:
    id: int
    user_id: int
    tag_id: int
