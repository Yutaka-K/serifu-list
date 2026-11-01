"""どの形式の台本でも使える、台詞欄の読み取り処理。"""
from __future__ import annotations

import re
import unicodedata
from typing import List, Optional, Tuple

from ..models import Line
from ..settings import Settings

# 「台詞なし」を表す記号
NO_LINE_MARKS = {"", "―", "—", "─", "－", "-", "ー", "‐", "なし", "（なし）"}

# 1つのコマに複数の台詞があるときの区切り
SEPARATORS = ("／", "/")

OPEN_QUOTES = "「『"
CLOSE_QUOTES = "」』"

# 話者のあとに付く（心）などの括弧
_PAREN_RE = re.compile(r"[（(]([^（）()]*)[）)]")


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


def split_items(cell: str) -> List[str]:
    """台詞欄を「／」で区切る。ただし「」の中の「／」では区切らない。"""
    cell = re.sub(r"<br\s*/?>", "／", cell, flags=re.IGNORECASE)
    items, buf, depth = [], [], 0
    for ch in cell:
        if ch in OPEN_QUOTES:
            depth += 1
        elif ch in CLOSE_QUOTES and depth > 0:
            depth -= 1
        if ch in SEPARATORS and depth == 0:
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    items.append("".join(buf).strip())
    return items


def is_no_line(cell: str) -> bool:
    return cell.strip() in NO_LINE_MARKS


def parse_item(item: str, settings: Settings) -> Tuple[Optional[Line], Optional[str]]:
    """台詞1つ（例：結衣（心）「……」）を読み取る。

    戻り値：(読み取れた台詞, 読めなかったときの理由)
    """
    raw = item.strip()
    s = raw.replace("**", "")  # Markdown の太字記号は無視

    start = next((i for i, c in enumerate(s) if c in OPEN_QUOTES), -1)
    if start < 0:
        return None, "「」（かぎかっこ）が見つかりません"
    close = CLOSE_QUOTES[OPEN_QUOTES.index(s[start])]
    end = s.rfind(close)
    if end <= start:
        return None, f"閉じかっこ（{close}）が見つかりません（閉じ忘れ？）"
    rest = s[end + 1 :].strip()
    if rest:
        return None, f"閉じかっこ（{close}）のあとに余分な文字「{rest}」があります。複数の台詞は「／」で区切ってください"

    text = s[start + 1 : end]
    head = s[:start].strip()

    # 話者と（ ）の注記を分ける
    notes = [n.strip() for n in _PAREN_RE.findall(head)]
    name = _PAREN_RE.sub("", head).strip()
    if re.search(r"[（）()]", name):
        return None, "話者名の（ ）の閉じ忘れなど、括弧の書き方が読めません"

    se_names = {nfkc(n).upper() for n in settings.se_speakers}
    if name and nfkc(name).upper() in se_names:
        kind = "効果音" + "".join(f"（{n}）" for n in notes if n)
        return Line(speaker=name, kind=kind, text=text, is_se=True, raw=raw), None

    if not name:
        return None, "話者名が書かれていません（例：結衣「……」）"

    if notes:
        first = settings.kind_names.get(notes[0], notes[0])
        kind = first + "".join(f"（{n}）" for n in notes[1:] if n)
    else:
        kind = "台詞"
    return Line(speaker=name, kind=kind, text=text, is_se=False, raw=raw), None
