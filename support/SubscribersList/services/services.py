import os
import shutil
import datetime

import pure_sha256
from models import User, Worker, Publication, Tag, Like, Subscription
import exporters


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class AuthService:
    def __init__(self, repos):
        self.repos = repos

    def register_user(self, login, password, email=None, gender=None, birth_year=None):
        login = (login or "").strip()
        if len(login) < 3:
            return None, "Логин должен быть не короче 3 символов."
        if self.repos["users"].find_by_login(login) is not None:
            return None, "Логин уже занят."
        if not password or len(password) < 6:
            return None, "Пароль должен быть не короче 6 символов."
        u = User(id=self.repos["users"].next_id(), login=login,
                 password_hash=pure_sha256.sha256_hex(password),
                 gender=(gender or None), birth_year=birth_year, email=(email or None))
        self.repos["users"].add(u)
        return u, None

    def register_worker(self, login, password):
        login = (login or "").strip()
        if len(login) < 3:
            return None, "Логин должен быть не короче 3 символов."
        if self.repos["workers"].find_by_login(login) is not None:
            return None, "Логин уже занят."
        if not password or len(password) < 6:
            return None, "Пароль должен быть не короче 6 символов."
        w = Worker(id=self.repos["workers"].next_id(), login=login,
                   password_hash=pure_sha256.sha256_hex(password))
        self.repos["workers"].add(w)
        return w, None

    def login_user(self, login, password):
        u = self.repos["users"].find_by_login(login or "")
        if u is None:
            return None, "Пользователь не найден."
        if u.password_hash != pure_sha256.sha256_hex(password or ""):
            return None, "Неверный пароль."
        return u, None

    def login_worker(self, login, password):
        w = self.repos["workers"].find_by_login(login or "")
        if w is None:
            return None, "Работник не найден."
        if w.password_hash != pure_sha256.sha256_hex(password or ""):
            return None, "Неверный пароль."
        return w, None


class PublicationService:
    def __init__(self, repos, media_dir=None):
        self.repos = repos
        self.media_dir = media_dir or "выпуски"

    def create_publication(self, worker, title, tags=None, file_src=None):
        title = (title or "").strip()
        if not title:
            return None, "Заголовок не может быть пустым."
        if not isinstance(worker, Worker):
            return None, "Автор не найден."
        resolved = self.repos["workers"].find_by_login(worker.login)
        if resolved is None or resolved.id != worker.id:
            return None, "Автор не найден."
        worker = resolved
        tag_names = [t.strip() for t in (tags or []) if t and t.strip()]
        now = _now()
        pub = Publication(id=self.repos["publications"].next_id(), title=title,
                          author_id=worker.id, tag_names=tag_names,
                          created_at=now, updated_at=now)
        if file_src and os.path.exists(file_src):
            os.makedirs(self.media_dir, exist_ok=True)
            dest = os.path.join(self.media_dir, os.path.basename(file_src))
            shutil.copyfile(file_src, dest)
            pub.file_path = dest
        self.repos["publications"].add(pub)
        for name in tag_names:
            self.repos["tags"].get_or_create(name)
        return pub, None

    def update_publication(self, worker, pub_id, title=None, tags=None):
        pub = self.repos["publications"].get(pub_id)
        if pub is None:
            return None, "Выпуск не найден."
        if not self.is_author(pub_id, worker):
            return None, "Вы не автор этого выпуска."
        if title is not None:
            title = title.strip()
            if not title:
                return None, "Заголовок не может быть пустым."
            pub.title = title
        if tags is not None:
            tag_names = [t.strip() for t in tags if t and t.strip()]
            pub.tag_names = tag_names
            for name in tag_names:
                self.repos["tags"].get_or_create(name)
        pub.updated_at = _now()
        self.repos["publications"].update(pub)
        return pub, None

    def delete_publication(self, worker, pub_id):
        pub = self.repos["publications"].get(pub_id)
        if pub is None:
            return False, "Выпуск не найден."
        if not self.is_author(pub_id, worker):
            return False, "Вы не автор этого выпуска."
        self.repos["likes"].remove_all_for_publication(pub_id)
        self.repos["publications"].delete(pub_id)
        return True, "Выпуск удалён."

    def is_author(self, pub_id, worker):
        """Действующее лицо — объект Worker. ID читателей и работников считаются
        независимо, поэтому принимаем только настоящий объект работника: иначе
        числовое совпадение ID делало бы читателя «автором» чужого выпуска."""
        pub = self.repos["publications"].get(pub_id)
        if pub is None or not isinstance(worker, Worker):
            return False
        author = self.repos["workers"].get(pub.author_id)
        if author is None or author.login.lower() != worker.login.lower():
            return False
        verified = self.repos["workers"].find_by_login(worker.login)
        return verified is not None and verified.id == worker.id

    def toggle_like(self, user_id, pub_id):
        if self.repos["publications"].get(pub_id) is None:
            return None, "Выпуск не найден."
        if self.repos["likes"].exists(pub_id, user_id):
            self.repos["likes"].remove(pub_id, user_id)
            return "removed", None
        self.repos["likes"].add(pub_id, user_id)
        return "added", None

    def toggle_subscription(self, user_id, tag_id):
        if self.repos["tags"].get(tag_id) is None:
            return None, "Метка не найдена."
        if self.repos["subscriptions"].exists(user_id, tag_id):
            self.repos["subscriptions"].remove(user_id, tag_id)
            return "removed", None
        self.repos["subscriptions"].add(user_id, tag_id)
        return "added", None

    def user_subscriptions(self, user_id):
        return self.repos["subscriptions"].for_user(user_id)

    def publications_of_worker(self, worker_id):
        return [p for p in self.repos["publications"].all() if p.author_id == worker_id]


class StatsService:
    def __init__(self, repos):
        self.repos = repos

    def tag_popularity(self):
        counts = {}
        for t in self.repos["tags"].all():
            cnt = 0
            for p in self.repos["publications"].all():
                if any(x.lower() == t.value.lower() for x in p.tag_names):
                    cnt += 1
            counts[t.value] = cnt
        return counts

    def gender_distribution(self):
        d = {"м": 0, "ж": 0, "не указан": 0}
        for u in self.repos["users"].all():
            key = (u.gender or "").strip().lower()
            if key not in ("м", "ж"):
                key = "не указан"
            d[key] += 1
        return d

    def age_groups(self):
        d = {"до 18": 0, "18-25": 0, "26-40": 0, "41+": 0, "не указан": 0}
        year = datetime.datetime.now().year
        for u in self.repos["users"].all():
            if not u.birth_year:
                d["не указан"] += 1
                continue
            age = year - int(u.birth_year)
            if age < 18:
                d["до 18"] += 1
            elif age <= 25:
                d["18-25"] += 1
            elif age <= 40:
                d["26-40"] += 1
            else:
                d["41+"] += 1
        return d

    def export_rows(self, table):
        users = self.repos["users"].all()
        if table == "Пользователи":
            return [{"id": u.id, "Логин": u.login, "Пол": u.gender,
                     "Год рождения": u.birth_year, "Email": u.email} for u in users]
        if table == "Публикации":
            rows = []
            for p in self.repos["publications"].all():
                author = self.repos["workers"].get(p.author_id)
                liked = []
                for l in self.repos["likes"].for_publication(p.id):
                    u = next((x for x in users if x.id == l.user_id), None)
                    if u is not None:
                        liked.append({"Логин": u.login})
                rows.append({
                    "id": p.id,
                    "Название": p.title,
                    "Автор": {"Логин": author.login if author else None},
                    "Метки": [{"Название": t} for t in p.tag_names],
                    "Оценили": liked,
                    "Файл": p.file_path,
                })
            return rows
        if table == "СписокМеток":
            rows = []
            for t in self.repos["tags"].all():
                subs = []
                for s in self.repos["subscriptions"].all():
                    if s.tag_id == t.id:
                        u = next((x for x in users if x.id == s.user_id), None)
                        if u is not None:
                            subs.append({"Логин": u.login})
                rows.append({"id": t.id, "Метка": t.value, "Подписчики": subs})
            return rows
        raise ValueError("Неизвестная таблица: " + str(table))

    def export_all(self, out_dir):
        written = []
        for name in ("Пользователи", "Публикации", "СписокМеток"):
            folder = os.path.join(out_dir, name)
            written.append((name, exporters.write_all(self.export_rows(name), folder)))
        return written


class App:
    def __init__(self, repos, media_dir=None):
        self.repos = repos
        self.auth = AuthService(repos)
        self.pubs = PublicationService(repos, media_dir)
        self.stats = StatsService(repos)

    def export_tables(self, out_dir):
        return self.stats.export_all(out_dir)
