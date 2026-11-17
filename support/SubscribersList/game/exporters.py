import os
import io
import csv
import json
import re
import xml.etree.ElementTree as ET

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$")
_SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ._-/")
_SAFE |= set(u"абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")


def _yaml_scalar(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "":
        return '""'
    ok = (s.strip() == s and all(ch in _SAFE for ch in s)
          and not s.startswith("-") and ":" not in s and "#" not in s)
    if ok:
        return s
    body = s.replace(chr(92), chr(92) + chr(92))
    body = body.replace('"', chr(92) + '"')
    body = body.replace(chr(10), chr(92) + "n")
    body = body.replace(chr(9), chr(92) + "t")
    return '"' + body + '"'


def _yaml_value(v, indent, out):
    pad = "  " * indent
    if isinstance(v, dict):
        if not v:
            out.append(pad + "{}")
            return
        for k, val in v.items():
            key = _yaml_scalar(k)
            if isinstance(val, dict) and not val:
                out.append(pad + key + ": {}")
            elif isinstance(val, list) and not val:
                out.append(pad + key + ": []")
            elif isinstance(val, (dict, list)):
                out.append(pad + key + ":")
                _yaml_value(val, indent + 1, out)
            else:
                out.append(pad + key + ": " + _yaml_scalar(val))
    elif isinstance(v, list):
        if not v:
            out.append(pad + "[]")
            return
        for item in v:
            if isinstance(item, dict) and item:
                first = True
                for k, val in item.items():
                    prefix = "- " if first else "  "
                    first = False
                    key = _yaml_scalar(k)
                    if isinstance(val, dict) and not val:
                        out.append(pad + prefix + key + ": {}")
                    elif isinstance(val, list) and not val:
                        out.append(pad + prefix + key + ": []")
                    elif isinstance(val, (dict, list)):
                        out.append(pad + prefix + key + ":")
                        _yaml_value(val, indent + 2, out)
                    else:
                        out.append(pad + prefix + key + ": " + _yaml_scalar(val))
            elif isinstance(item, list) and item:
                out.append(pad + "-")
                _yaml_value(item, indent + 1, out)
            else:
                out.append(pad + "- " + _yaml_scalar(item))


def export_yaml(rows, path):
    out = []
    _yaml_value(list(rows), 0, out)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(chr(10).join(out) + chr(10))


def export_json(rows, path):
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(list(rows), f, ensure_ascii=False, indent=2)


def _flatten(v):
    """Вложенные структуры — в одну строку для CSV."""
    if isinstance(v, dict):
        return "; ".join(_yaml_scalar(k) + "=" + _flatten(x) for k, x in v.items())
    if isinstance(v, list):
        return "; ".join(_flatten(x) for x in v)
    if v is None:
        return ""
    return str(v)


def export_csv(rows, path):
    rows = list(rows)
    keys = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        for r in rows:
            writer.writerow([_flatten(r.get(k)) for k in keys])


def _xml_name(name):
    out = []
    for ch in str(name):
        if ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    s = "".join(out) or "field"
    if s[0].isdigit():
        s = "_" + s
    return s


def _xml_fill(parent, key, val):
    el = ET.SubElement(parent, _xml_name(key))
    if isinstance(val, dict):
        for k, v in val.items():
            _xml_fill(el, k, v)
    elif isinstance(val, list):
        for item in val:
            if isinstance(item, dict):
                sub = ET.SubElement(el, "item")
                for k, v in item.items():
                    _xml_fill(sub, k, v)
            else:
                it = ET.SubElement(el, "item")
                it.text = "" if item is None else str(item)
    else:
        el.text = "" if val is None else str(val)


def export_xml(rows, path):
    root = ET.Element("records")
    for r in rows:
        rec = ET.SubElement(root, "record")
        for k, v in r.items():
            _xml_fill(rec, k, v)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def write_all(rows, out_dir):
    """Четыре файла из одних данных; папка создаётся автоматически."""
    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "json": os.path.join(out_dir, "data.json"),
        "csv": os.path.join(out_dir, "data.csv"),
        "xml": os.path.join(out_dir, "data.xml"),
        "yaml": os.path.join(out_dir, "data.yaml"),
    }
    export_json(rows, paths["json"])
    export_csv(rows, paths["csv"])
    export_xml(rows, paths["xml"])
    export_yaml(rows, paths["yaml"])
    return paths
