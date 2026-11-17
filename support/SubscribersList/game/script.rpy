init python:
    import os
    import models as _m
    import json_repositories as _jr
    import services as _sv
    import exporters as _ex

    def _data_path():
        try:
            base = renpy.config.gamedir
        except Exception:
            base = "."
        return os.path.join(os.path.abspath(base), "almanah_data.json")

    def _ask(prompt):
        return renpy.input(prompt, default="").strip()

    def _ask_password(prompt):
        return renpy.input(prompt, default="", mask="*").strip()

    def _ensure_svc():
        if store.svc is None:
            media = os.path.join(os.path.dirname(_data_path()), "выпуски")
            store.svc = _sv.App(_jr.create_repositories(_data_path()), media)
        return store.svc

    def _note(msg):
        store._msg = msg
        renpy.restart_interaction()

    def _pub_rows():
        svc = _ensure_svc()
        rows = []
        for p in svc.repos["publications"].all():
            cnt = len(svc.repos["likes"].for_publication(p.id))
            rows.append({"id": p.id, "title": p.title,
                        "tags": ", ".join(p.tag_names), "likes": cnt})
        return rows

    def _is_liked(pid):
        svc = _ensure_svc()
        if store.cur_user is None:
            return False
        return svc.repos["likes"].exists(pid, store.cur_user.id)

    def _do_like(pid):
        svc = _ensure_svc()
        svc.pubs.toggle_like(store.cur_user.id, pid)
        renpy.restart_interaction()

    def _tag_rows():
        svc = _ensure_svc()
        rows = []
        for t in svc.repos["tags"].all():
            cnt = len(svc.repos["subscriptions"].for_tag(t.id))
            rows.append({"name": t.value, "subs": cnt, "tag_id": t.id})
        return rows

    def _is_subscribed(tid):
        svc = _ensure_svc()
        if store.cur_user is None:
            return False
        return svc.repos["subscriptions"].exists(store.cur_user.id, tid)

    def _do_sub(tid):
        svc = _ensure_svc()
        svc.pubs.toggle_subscription(store.cur_user.id, tid)
        renpy.restart_interaction()

    def _my_pubs():
        svc = _ensure_svc()
        return svc.pubs.publications_of_worker(store.cur_worker.id)

    def _do_delete(pid):
        svc = _ensure_svc()
        ok, err = svc.pubs.delete_publication(store.cur_worker.id, pid)
        renpy.restart_interaction()

    def _bar(label, count, total):
        filled = int(round(30.0 * count / total)) if total else 0
        return label + " " + ("█" * filled) + " (" + str(count) + ")"

    def _tag_bars():
        d = _ensure_svc().stats.tag_popularity()
        mx = max([v for v in d.values()] or [1]) or 1
        return [_bar(k, v, mx) for k, v in sorted(d.items(), key=lambda kv: -kv[1])]

    def _gender_bars():
        d = _ensure_svc().stats.gender_distribution()
        mx = max([v for v in d.values()] or [1]) or 1
        return [_bar(k, v, mx) for k, v in d.items()]

    def _pub_bars():
        svc = _ensure_svc()
        lines = []
        for p in svc.repos["publications"].all():
            cnt = len(svc.repos["likes"].for_publication(p.id))
            lines.append(_bar(p.title, cnt, max(cnt, 1)))
        return lines or ["Выпусков пока нет"]

    def _age_bars():
        d = _ensure_svc().stats.age_groups()
        mx = max([v for v in d.values()] or [1]) or 1
        return [_bar(k, v, mx) for k, v in d.items()]


default svc = None
default cur_user = None
default cur_worker = None
default msg = ""

style panel is frame:
    background Frame("#2c2c4a", 12, 12)
    padding (30, 30)

style menu_btn is button:
    xfill True
    xmargin 0
    ymargin 4
    background Frame("#3a3a5c", 8, 8)
    hover_background Frame("#4a4a7c", 8, 8)

style menu_btn_text is text:
    size 22
    color "#f0f0f0"
    hover_color "#ffd54a"
    xalign 0.5

screen main_menu_screen():
    modal True
    add Solid("#16162a")
    frame:
        style "panel"
        xalign 0.5 yalign 0.5
        vbox:
            spacing 14
            text "Альманах" size 34 color "#f5f5f5" xalign 0.5
            text "журнал учёта самых заинтересованных читателей" size 24 color "#aaa9a9" xalign 0.5
            if msg:
                text _msg size 16 color "#ffd54a" xalign 0.5
            textbutton "Вход читателя" action Jump("flow_login_user"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Регистрация читателя" action Jump("flow_register_user"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Вход работника" action Jump("flow_login_worker"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Регистрация работника" action Jump("flow_register_worker"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Справка" action Jump("flow_help"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Выход" action Quit(confirm=False):
                style "menu_btn"
                text_style "menu_btn_text"

screen reader_menu_screen():
    modal True
    add Solid("#16162a")
    frame:
        style "panel"
        xalign 0.5 yalign 0.5
        vbox:
            spacing 12
            text "Читатель: [cur_user.login]" size 26 color "#f5f5f5" xalign 0.5
            if _msg:
                text _msg size 16 color "#ffd54a" xalign 0.5
            textbutton "Каталог выпусков" action Jump("flow_catalog"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Мои подписки" action Jump("flow_subscriptions"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Сменить пользователя" action Jump("main_loop"):
                style "menu_btn"
                text_style "menu_btn_text"

screen catalog_screen():
    modal True
    add Solid("#16162a")
    frame:
        style "panel"
        xalign 0.5 yalign 0.5
        vbox:
            spacing 10
            text "Каталог выпусков" size 30 color "#f5f5f5" xalign 0.5
            viewport:
                xmaximum 780 ymaximum 380
                scrollbars "vertical"
                mousewheel True
                vbox:
                    spacing 8
                    for row in _pub_rows():
                        hbox:
                            spacing 14
                            text "[row[title]]" size 22 min_width 360 color "#f0f0f0"
                            text "Метки: [row[tags]]" size 16 color "#9aa6d0"
                            text "Оценок: [row[likes]]" size 16 color "#ffd54a"
                            if store.cur_user is not None:
                                if _is_liked(row[id]):
                                    textbutton "Снять оценку" action Function(_do_like, row[id])
                                else:
                                    textbutton "Оценить" action Function(_do_like, row[id])
            textbutton "Назад" action Jump("reader_menu_loop"):
                style "menu_btn"
                text_style "menu_btn_text"

screen subscriptions_screen():
    modal True
    add Solid("#16162a")
    frame:
        style "panel"
        xalign 0.5 yalign 0.5
        vbox:
            spacing 10
            text "Мои подписки" size 30 color "#f5f5f5" xalign 0.5
            viewport:
                xmaximum 780 ymaximum 380
                scrollbars "vertical"
                mousewheel True
                vbox:
                    spacing 8
                    for row in _tag_rows():
                        hbox:
                            spacing 14
                            text "[row[name]] (подписчиков: [row[subs]])" size 22 color "#f0f0f0"
                            if _is_subscribed(row[tag_id]):
                                textbutton "Отписаться" action Function(_do_sub, row[tag_id])
                            else:
                                textbutton "Подписаться" action Function(_do_sub, row[tag_id])
            textbutton "Назад" action Jump("reader_menu_loop"):
                style "menu_btn"
                text_style "menu_btn_text"

screen worker_menu_screen():
    modal True
    add Solid("#16162a")
    frame:
        style "panel"
        xalign 0.5 yalign 0.5
        vbox:
            spacing 12
            text "Работник: [cur_worker.login]" size 26 color "#f5f5f5" xalign 0.5
            if _msg:
                text _msg size 16 color "#ffd54a" xalign 0.5
            textbutton "Создать выпуск" action Jump("flow_create_pub"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Мои выпуски" action Jump("flow_my_pubs"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Статистика" action Jump("flow_stats"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Диаграммы" action Jump("flow_charts"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Экспорт данных (out)" action Jump("flow_export"):
                style "menu_btn"
                text_style "menu_btn_text"
            textbutton "Сменить пользователя" action Jump("main_loop"):
                style "menu_btn"
                text_style "menu_btn_text"

screen my_pubs_screen():
    modal True
    add Solid("#16162a")
    frame:
        style "panel"
        xalign 0.5 yalign 0.5
        vbox:
            spacing 10
            text "Мои выпуски" size 30 color "#f5f5f5" xalign 0.5
            viewport:
                xmaximum 780 ymaximum 380
                scrollbars "vertical"
                mousewheel True
                vbox:
                    spacing 8
                    for p in _my_pubs():
                        hbox:
                            spacing 14
                            text "[p.title]" size 22 min_width 380 color "#f0f0f0"
                            textbutton "Редактировать" action Call("flow_edit_pub", pid=p.id)
                            textbutton "Удалить" action Call("flow_delete_pub", pid=p.id)
            textbutton "Назад" action Jump("worker_menu_loop"):
                style "menu_btn"
                text_style "menu_btn_text"

screen stats_screen():
    modal True
    add Solid("#16162a")
    frame:
        style "panel"
        xalign 0.5 yalign 0.5
        vbox:
            spacing 10
            text "Статистика" size 30 color "#f5f5f5" xalign 0.5
            viewport:
                xmaximum 780 ymaximum 400
                scrollbars "vertical"
                mousewheel True
                vbox:
                    spacing 6
                    text "Популярность меток:" size 20 color "#9aa6d0"
                    for line in _tag_bars():
                        text line size 18 color "#f0f0f0"
                    text "Распределение по полу:" size 20 color "#9aa6d0"
                    for line in _gender_bars():
                        text line size 18 color "#f0f0f0"
                    text "Возрастные группы:" size 20 color "#9aa6d0"
                    for line in _age_bars():
                        text line size 18 color "#f0f0f0"
            textbutton "Назад" action Jump("worker_menu_loop"):
                style "menu_btn"
                text_style "menu_btn_text"

screen charts_screen():
    modal True
    add Solid("#16162a")
    frame:
        style "panel"
        xalign 0.5 yalign 0.5
        vbox:
            spacing 10
            text "Диаграммы" size 30 color "#f5f5f5" xalign 0.5
            viewport:
                xmaximum 780 ymaximum 400
                scrollbars "vertical"
                mousewheel True
                vbox:
                    spacing 8
                    text "Оценки выпусков:" size 20 color "#9aa6d0"
                    for line in _pub_bars():
                        text line size 18 color "#f0f0f0"
            textbutton "Назад" action Jump("worker_menu_loop"):
                style "menu_btn"
                text_style "menu_btn_text"

screen help_screen():
    modal True
    add Solid("#16162a")
    frame:
        style "panel"
        xalign 0.5 yalign 0.5
        vbox:
            spacing 10
            text "Справка" size 30 color "#f5f5f5" xalign 0.5
            viewport:
                xmaximum 780 ymaximum 380
                scrollbars "vertical"
                mousewheel True
                vbox:
                    spacing 6
                    text "Читатель: регистрируется, входит, оценивает выпуски, подписывается на метки." size 18 color "#f0f0f0"
                    text "Работник: публикует выпуски с файлами и метками, редактирует и удаляет их." size 18 color "#f0f0f0"
                    text "Статистика и диаграммы доступны работнику: метки, пол, возраст, оценки." size 18 color "#f0f0f0"
                    text "Экспорт сохраняет выбранные таблицы в JSON, CSV, XML и YAML (папка out)." size 18 color "#f0f0f0"
            textbutton "Назад" action Jump("main_loop"):
                style "menu_btn"
                text_style "menu_btn_text"

# ============================================================
# Метки: игровая логика
# ============================================================

label start:
    scene black with None
    jump main_loop

label main_loop:
    $ renpy.transition(Dissolve(0.4))
    call screen main_menu_screen

label flow_help:
    $ renpy.transition(Dissolve(0.4))
    call screen help_screen

label flow_login_user:
    $ _ensure_svc()
    $ _login = _ask("Логин:")
    if _login == "":
        $ _note("Ввод отменён.")
        jump main_loop
    $ _pwd = _ask_password("Пароль:")
    python:
        user, err = svc.auth.login_user(_login, _pwd)
    if err:
        $ _note(err)
        jump main_loop
    python:
        store.cur_user = user
        store.cur_worker = None
    $ _note("Добро пожаловать, " + user.login + "!")
    jump reader_menu_loop

label flow_register_user:
    $ _ensure_svc()
    $ _login = _ask("Придумайте логин (не менее 3 символов):")
    if _login == "":
        $ _note("Ввод отменён.")
        jump main_loop
    $ _pwd = _ask_password("Придумайте пароль (не менее 6 символов):")
    $ _email = _ask("Email (необязательно):")
    $ _gender = _ask("Пол (м/ж, необязательно):")
    $ _by = _ask("Год рождения (необязательно):")
    python:
        gender = _gender or None
        by = None
        if _by.isdigit():
            by = int(_by)
        user, err = svc.auth.register_user(_login, _pwd, _email or None, gender, by)
    if err:
        $ _note(err)
        jump main_loop
    python:
        store.cur_user = user
        store.cur_worker = None
    $ _note("Аккаунт создан. Добро пожаловать, " + user.login + "!")
    jump reader_menu_loop

label flow_login_worker:
    $ _ensure_svc()
    $ _login = _ask("Логин работника:")
    if _login == "":
        $ _note("Ввод отменён.")
        jump main_loop
    $ _pwd = _ask_password("Пароль:")
    python:
        worker, err = svc.auth.login_worker(_login, _pwd)
    if err:
        $ _note(err)
        jump main_loop
    python:
        store.cur_worker = worker
        store.cur_user = None
    $ _note("Здравствуйте, " + worker.login + "!")
    jump worker_menu_loop

label flow_register_worker:
    $ _ensure_svc()
    $ _login = _ask("Придумайте логин работника (не менее 3 символов):")
    if _login == "":
        $ _note("Ввод отменён.")
        jump main_loop
    $ _pwd = _ask_password("Придумайте пароль (не менее 6 символов):")
    python:
        worker, err = svc.auth.register_worker(_login, _pwd)
    if err:
        $ _note(err)
        jump main_loop
    python:
        store.cur_worker = worker
        store.cur_user = None
    $ _note("Аккаунт работника создан: " + worker.login)
    jump worker_menu_loop

label reader_menu_loop:
    $ renpy.transition(Dissolve(0.4))
    call screen reader_menu_screen

label worker_menu_loop:
    $ renpy.transition(Dissolve(0.4))
    call screen worker_menu_screen

label flow_catalog:
    $ renpy.transition(Dissolve(0.4))
    call screen catalog_screen

label flow_subscriptions:
    $ renpy.transition(Dissolve(0.4))
    call screen subscriptions_screen

label flow_create_pub:
    $ _ensure_svc()
    $ _title = _ask("Заголовок выпуска:")
    if _title == "":
        $ _note("Ввод отменён.")
        jump worker_menu_loop
    $ _tags_raw = _ask("Метки через запятую (можно пусто):")
    $ _fsrc = _ask("Путь к файлу (можно пусто):")
    python:
        tags = [t for t in _tags_raw.split(",") if t.strip()]
        pub, err = svc.pubs.create_publication(cur_worker, _title, tags, _fsrc or None)
    if err:
        $ _note(err)
    else:
        $ _note("Выпуск создан: " + pub.title)
    jump worker_menu_loop

label flow_my_pubs:
    $ renpy.transition(Dissolve(0.4))
    call screen my_pubs_screen

label flow_edit_pub(pid=0):
    $ _ensure_svc()
    python:
        pub = svc.repos["publications"].get(pid)
        if pub is None:
            err = "Выпуск не найден."
            pub = None
        else:
            err = None
    if err:
        $ _note(err)
        jump worker_menu_loop
    $ _new_title = _ask("Новый заголовок (пусто — не менять):")
    $ _new_tags = _ask("Новые метки через запятую (пусто — не менять):")
    python:
        title = _new_title if _new_title else None
        tags = [t.strip() for t in _new_tags.split(",") if t.strip()] if _new_tags else None
        pub, err = svc.pubs.update_publication(cur_worker, pid, title, tags)
    if err:
        $ _note(err)
    else:
        $ _note("Выпуск обновлён.")
    jump worker_menu_loop

label flow_delete_pub(pid=0):
    $ _ensure_svc()
    menu:
        "Удалить выпуск?"
        "Да":
            python:
                ok, err = svc.pubs.delete_publication(cur_worker, pid)
            $ _note(err)
        "Нет":
            $ _note("Удаление отменено.")
    jump worker_menu_loop

label flow_stats:
    $ renpy.transition(Dissolve(0.4))
    call screen stats_screen

label flow_charts:
    $ renpy.transition(Dissolve(0.4))
    call screen charts_screen

label flow_export:
    $ _ensure_svc()
    python:
        try:
            outdir = os.path.join(os.path.dirname(_data_path()), "out")
            written = svc.export_tables(outdir)
            _note("Экспорт завершён: " + outdir)
        except Exception as e:
            _note("Ошибка экспорта: " + str(e))
    jump worker_menu_loop
