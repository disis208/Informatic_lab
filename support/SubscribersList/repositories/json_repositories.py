import os
import io
import json
from dataclasses import asdict
from typing import List, Optional

from models import User, Worker, Publication, Tag, Like, Subscription


class _Store:
    """Общее хранилище: один файл, все шесть таблиц внутри."""

    TABLES = ("users", "workers", "publications", "tags", "likes", "subscriptions")

    def __init__(self, path):
        self.path = path
        self.data = {t: [] for t in self.TABLES}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with io.open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)

    def save(self):
        folder = os.path.dirname(os.path.abspath(self.path))
        if folder:
            os.makedirs(folder, exist_ok=True)
        with io.open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def next_id(self, key):
        rows = self.data[key]
        return max([r["id"] for r in rows], default=0) + 1


_store_cache = {}


def _get_store(path):
    """Один файл — одно хранилище на весь процесс (репозитории делят данные)."""
    ap = os.path.abspath(path)
    if ap not in _store_cache:
        _store_cache[ap] = _Store(ap)
    return _store_cache[ap]


class _BaseRepo:
    key = ""
    cls = None

    def __init__(self, store):
        self.store = store

    def all(self):
        return [self.cls(**r) for r in self.store.data[self.key]]

    def get(self, item_id):
        for r in self.store.data[self.key]:
            if r["id"] == item_id:
                return self.cls(**r)
        return None

    def next_id(self):
        return self.store.next_id(self.key)

    def add(self, obj):
        self.store.data[self.key].append(asdict(obj))
        self.store.save()

    def delete(self, item_id):
        self.store.data[self.key] = [r for r in self.store.data[self.key]
                                     if r["id"] != item_id]
        self.store.save()


class UserRepository(_BaseRepo):
    key = "users"
    cls = User

    def find_by_login(self, login):
        """Сравнение регистра на стороне Python: SQLite lower() не знает кириллицу."""
        needle = (login or "").strip().lower()
        for r in self.store.data[self.key]:
            if r["login"].strip().lower() == needle:
                return self.cls(**r)
        return None


class WorkerRepository(_BaseRepo):
    key = "workers"
    cls = Worker

    def find_by_login(self, login):
        needle = (login or "").strip().lower()
        for r in self.store.data[self.key]:
            if r["login"].strip().lower() == needle:
                return self.cls(**r)
        return None


class PublicationRepository(_BaseRepo):
    key = "publications"
    cls = Publication

    def update(self, pub):
        rows = self.store.data[self.key]
        for i, r in enumerate(rows):
            if r["id"] == pub.id:
                rows[i] = asdict(pub)
                break
        self.store.save()


class TagRepository(_BaseRepo):
    key = "tags"
    cls = Tag

    def find_by_value(self, value):
        needle = (value or "").strip().lower()
        for r in self.store.data[self.key]:
            if r["value"].strip().lower() == needle:
                return self.cls(**r)
        return None

    def get_or_create(self, value):
        """Схлопывание регистра: «Наука» и «наука» — одна метка."""
        found = self.find_by_value(value)
        if found is not None:
            return found
        t = Tag(id=self.next_id(), value=(value or "").strip())
        self.add(t)
        return t


class LikeRepository(_BaseRepo):
    key = "likes"
    cls = Like

    def for_publication(self, pub_id):
        return [self.cls(**r) for r in self.store.data[self.key]
                if r["publication_id"] == pub_id]

    def exists(self, pub_id, user_id):
        return any(r["publication_id"] == pub_id and r["user_id"] == user_id
                   for r in self.store.data[self.key])

    def add(self, pub_id, user_id):
        self.add_id(self.next_id(), pub_id, user_id)

    def add_id(self, like_id, pub_id, user_id):
        self.store.data[self.key].append(
            {"id": like_id, "publication_id": pub_id, "user_id": user_id})
        self.store.save()

    def remove(self, pub_id, user_id):
        self.store.data[self.key] = [r for r in self.store.data[self.key]
                                     if not (r["publication_id"] == pub_id
                                             and r["user_id"] == user_id)]
        self.store.save()

    def remove_all_for_publication(self, pub_id):
        self.store.data[self.key] = [r for r in self.store.data[self.key]
                                     if r["publication_id"] != pub_id]
        self.store.save()


class SubscriptionRepository(_BaseRepo):
    key = "subscriptions"
    cls = Subscription

    def for_user(self, user_id):
        return [self.cls(**r) for r in self.store.data[self.key]
                if r["user_id"] == user_id]

    def for_tag(self, tag_id):
        return [self.cls(**r) for r in self.store.data[self.key]
                if r["tag_id"] == tag_id]

    def all(self):
        return [self.cls(**r) for r in self.store.data[self.key]]

    def exists(self, user_id, tag_id):
        return any(r["user_id"] == user_id and r["tag_id"] == tag_id
                   for r in self.store.data[self.key])

    def add(self, user_id, tag_id):
        self.store.data[self.key].append(
            {"id": self.next_id(), "user_id": user_id, "tag_id": tag_id})
        self.store.save()

    def remove(self, user_id, tag_id):
        self.store.data[self.key] = [r for r in self.store.data[self.key]
                                     if not (r["user_id"] == user_id
                                             and r["tag_id"] == tag_id)]
        self.store.save()


def create_repositories(path):
    """Фабрика: все шесть репозиториев над общим хранилищем одного файла."""
    store = _get_store(path)
    return {
        "users": UserRepository(store),
        "workers": WorkerRepository(store),
        "publications": PublicationRepository(store),
        "tags": TagRepository(store),
        "likes": LikeRepository(store),
        "subscriptions": SubscriptionRepository(store),
    }
