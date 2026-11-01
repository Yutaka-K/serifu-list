"""4コマ漫画の台本を読み取る部分。

想定している書き方（第1話_台本.md と同じ形）：

    ### 01「バイト帰り」

    | コマ | 絵 | 台詞・音 |
    |---|---|---|
    | 1 | 夜。雨。…… | 結衣（心）「バイト終わりは……」 |
    | 2 | …… | SE「……ミー」／結衣「……ん？」 |

- 「### 番号「タイトル」」の見出しごとに1本
- 見出しの下にある、「コマ」と「台詞」の列がある表だけを読む
- それ以外（説明文・箇条書き・[提案] などの注記・[[リンク]]・ほかの表）は無視する
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from ..models import Panel, Problem, Script, Unit
from ..settings import Settings
from .common import is_no_line, nfkc, parse_item, split_items

# 例：### 01「バイト帰り」
_HEADING_RE = re.compile(r"^###(?!#)\s*(.*)$")
_HEADING_BODY_RE = re.compile(r"^(?:第)?\s*([0-9０-９]+)\s*(?:本|話)?\s*[.．:：、]?\s*(.*)$")
_SEPARATOR_ROW_RE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _split_row(line: str) -> List[str]:
    """表の1行を「|」で列に分ける（「\\|」は区切りとみなさない）。"""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells = re.split(r"(?<!\\)\|", s)
    return [c.replace("\\|", "|").strip() for c in cells]


def _strip_title(t: str) -> str:
    t = t.strip()
    if len(t) >= 2 and t[0] in "「『" and t[-1] in "」』":
        t = t[1:-1]
    return t.strip()


def _find_column(header: List[str], words) -> Optional[int]:
    for i, h in enumerate(header):
        if any(w in h for w in words):
            return i
    return None


def parse(text: str, path: Path, settings: Settings) -> Script:
    script = Script(path=path)
    lines = text.splitlines()

    unit: Optional[Unit] = None
    unit_has_table = False
    i = 0

    def finish_unit():
        if unit is not None and not unit_has_table:
            script.problems.append(
                Problem("読み取れない箇所", "この本に「コマ｜絵｜台詞・音」の表が見つかりません",
                        line_no=unit.source_line, unit=unit.label)
            )

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        line_no = i + 1

        # --- 見出し ---
        m = _HEADING_RE.match(stripped)
        if m:
            finish_unit()
            body = m.group(1).strip()
            hm = _HEADING_BODY_RE.match(body)
            if hm:
                number = nfkc(hm.group(1))
                title = _strip_title(hm.group(2))
            else:
                number, title = "", _strip_title(body)
                script.problems.append(
                    Problem("読み取れない箇所", "見出しに本番号が見つかりません（例：### 01「タイトル」）",
                            line_no=line_no, content=stripped)
                )
            unit = Unit(number=number, title=title, source_line=line_no)
            script.units.append(unit)
            unit_has_table = False
            i += 1
            continue

        # 「#」「##」の見出しや「---」の区切り線で、本の範囲は終わり
        if stripped.startswith("#") or re.fullmatch(r"-{3,}|\*{3,}|_{3,}", stripped):
            finish_unit()
            unit = None
            unit_has_table = False
            i += 1
            continue

        # --- 表 ---
        if stripped.startswith("|"):
            # 表のかたまりを全部取り出す
            table = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table.append((i + 1, lines[i]))
                i += 1
            if unit is not None:
                if _read_table(table, unit, script, settings):
                    unit_has_table = True
            continue

        i += 1

    finish_unit()
    return script


def _read_table(table, unit: Unit, script: Script, settings: Settings) -> bool:
    """コマの表を読む。コマの表でなければ False を返す（その表は無視）。"""
    header_no, header_line = table[0]
    header = _split_row(header_line)
    col_panel = _find_column(header, ["コマ"])
    col_line = _find_column(header, ["台詞", "セリフ", "せりふ", "音"])
    if col_panel is None or col_line is None:
        return False  # コマの表ではない
    col_pic = _find_column(header, ["絵", "内容", "ト書き"])

    rows = table[1:]
    if rows and _SEPARATOR_ROW_RE.match(rows[0][1].strip()):
        rows = rows[1:]

    for line_no, row_line in rows:
        cells = _split_row(row_line)
        if len(cells) != len(header):
            script.problems.append(
                Problem("読み取れない箇所",
                        f"表の列の数が見出し行（{len(header)}列）と合いません（この行は{len(cells)}列）。「|」の数を確かめてください",
                        line_no=line_no, unit=unit.label, content=row_line.strip())
            )
            if len(cells) <= max(col_panel, col_line):
                continue

        number_raw = cells[col_panel].strip()
        num_text = nfkc(number_raw).replace("コマ目", "").replace("コマ", "").strip()
        number = int(num_text) if num_text.isdigit() else None
        picture = cells[col_pic].strip() if col_pic is not None and col_pic < len(cells) else ""
        panel = Panel(number=number, number_raw=number_raw, picture=picture, source_line=line_no)
        unit.panels.append(panel)

        if number is None:
            script.problems.append(
                Problem("読み取れない箇所", f"コマ番号「{number_raw}」が数字として読めません",
                        line_no=line_no, unit=unit.label, content=row_line.strip())
            )

        cell = cells[col_line]
        if is_no_line(cell):
            continue
        for item in split_items(cell):
            if is_no_line(item):
                if item.strip():
                    continue
                script.problems.append(
                    Problem("読み取れない箇所", "「／」の前後が空になっています（区切りの打ちすぎ？）",
                            line_no=line_no, unit=unit.label, panel=panel.label, content=cell)
                )
                continue
            parsed, reason = parse_item(item, settings)
            if parsed is None:
                script.problems.append(
                    Problem("読み取れない箇所", reason, line_no=line_no, unit=unit.label,
                            panel=panel.label, content=item)
                )
            else:
                panel.lines.append(parsed)
    return True
