"""
Применяет правки из режима правки к контент-пакетам.

Порядок работы: edit.html → щёлкнуть по тексту, исправить → «Скачать правки» (файл pravki-….md) →
    python scripts/apply_edits.py pravki-….md --dry-run   # что изменится, без записи
    python scripts/apply_edits.py pravki-….md             # записать в content/*.md
    python scripts/build_site.py                          # пересобрать index.html и edit.html

Правило одно: без догадок. Правка применяется, только если текст «было» находится в своём файле
ровно один раз и после замены шапка пакета остаётся корректным YAML. Остальные правки скрипт
перечисляет с причиной и не трогает. Писать можно только в content/.
Зависимости: PyYAML.
"""
import json, re, sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"


def replacement(e):
    new = str(e["new"]).replace("\r", "").strip()
    if e["kind"] == "yaml":  # значение в двойных кавычках на одной строке
        new = re.sub(r"\s+", " ", new).replace("\\", "\\\\").replace('"', '\\"')
    return e["pre"] + new + e["suf"]


def valid(path, text):
    """Файл после правки читается так же, как его читает сборка."""
    try:
        if path.suffix == ".yml":
            yaml.safe_load(text)
        else:
            m = re.match(r"---\n(.*?)\n---\n", text.replace("\r\n", "\n"), re.S)
            if not m:
                return "пропала YAML-шапка"
            yaml.safe_load(m.group(1))
    except yaml.YAMLError as err:
        return f"шапка перестала читаться как YAML ({str(err).splitlines()[0]})"
    return None


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    dry = "--dry-run" in argv
    if len(args) != 1:
        sys.exit("Запуск: python scripts/apply_edits.py pravki-….md [--dry-run]")
    t = Path(args[0]).read_text(encoding="utf-8")
    m = re.search(r"<!-- edits-json\n(.*?)\n-->", t, re.S)
    if not m:
        sys.exit("В файле нет блока edits-json — это не выгрузка из edit.html?")
    edits = json.loads(m.group(1))

    texts, done, skipped = {}, [], []
    for i, e in enumerate(edits, 1):
        label = f"{i}. {e.get('where', '')} ({e['file']})"
        path = (ROOT / e["file"]).resolve()
        if CONTENT.resolve() not in path.parents or not path.exists():
            skipped.append((label, "файл не из content/ или его нет")); continue
        src = texts.get(path) or path.read_text(encoding="utf-8")
        repl = replacement(e)
        n = src.count(e["find"])
        if n != 1:
            why = ("уже применена" if repl in src else
                   "текста «было» в файле нет — пакет изменили после правки" if n == 0 else
                   f"текст «было» встречается {n} раза — непонятно, какой менять")
            skipped.append((label, why)); continue
        out = src.replace(e["find"], repl, 1)
        bad = valid(path, out)
        if bad:
            skipped.append((label, bad)); continue
        texts[path] = out
        done.append((label, e["orig"], e["new"], e.get("note", "")))

    for label, was, now, note in done:
        print(f"✓ {label}\n    было:  {was}\n    стало: {now}" + (f"\n    пометка: {note}" if note else ""))
    for label, why in skipped:
        print(f"✗ {label}: {why}")
    if not dry:
        for path, text in texts.items():
            path.write_text(text, encoding="utf-8", newline="\n")
    verb = "применимы" if dry else "применены"
    print(f"\nПравок в файле: {len(edits)} · {verb}: {len(done)} · пропущены: {len(skipped)}"
          + (" · проверка без записи" if dry else "")
          + ("" if dry or not done else " · теперь: python scripts/build_site.py"))
    return 1 if skipped and not all(w == "уже применена" for _, w in skipped) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
