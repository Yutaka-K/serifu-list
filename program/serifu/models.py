"""台本を読み取った結果を入れておく「入れ物」の定義。

読み取り部分（parsers フォルダ）は、台本をこの形に変換します。
出力部分（writers.py）とチェック部分（checks.py）は、この形だけを見て動きます。
そのため、台本の書き方が変わっても、読み取り部分を差し替えるだけで済みます。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Line:
    """台詞1つ分（効果音も含む）。"""

    speaker: str  # 話者（例：結衣、SE）
    kind: str  # 種類（例：台詞、心の声、効果音（奥））
    text: str  # 「」の中身
    is_se: bool  # 効果音なら True
    raw: str  # 台本に書かれていたそのままの文字

    @property
    def char_count(self) -> int:
        """文字数（半角・全角の空白は数えない）。"""
        return sum(1 for c in self.text if not c.isspace())


@dataclass
class Panel:
    """コマ1つ分。"""

    number: Optional[int]  # コマ番号（読めなかったときは None）
    number_raw: str  # 台本に書かれていたコマ番号の文字
    picture: str  # 絵の説明
    lines: List[Line] = field(default_factory=list)
    source_line: int = 0  # 台本の何行目か

    @property
    def label(self) -> str:
        return str(self.number) if self.number is not None else self.number_raw


@dataclass
class Unit:
    """まとまり1つ分。4コマ漫画なら「1本」、ページ単位の台本なら「1ページ」。"""

    number: str  # 本番号（例：01）
    title: str  # 本タイトル
    panels: List[Panel] = field(default_factory=list)
    source_line: int = 0

    @property
    def label(self) -> str:
        if self.title:
            return f"{self.number}「{self.title}」"
        return self.number


@dataclass
class Problem:
    """警告1件分。"""

    category: str  # 警告の種類（例：コマ数、長い台詞）
    message: str  # 説明
    line_no: Optional[int] = None  # 台本の何行目か
    unit: str = ""  # どの本か
    panel: str = ""  # どのコマか
    content: str = ""  # 問題の箇所の文字

    def to_text(self) -> str:
        where = []
        if self.line_no:
            where.append(f"{self.line_no}行目")
        if self.unit:
            where.append(self.unit)
        if self.panel:
            where.append(f"{self.panel}コマ目")
        head = f"［{self.category}］"
        if where:
            head += " " + "・".join(where) + "："
        else:
            head += " "
        text = head + self.message
        if self.content:
            text += f"\n      → {self.content}"
        return text


@dataclass
class Script:
    """台本1つ分を読み取った結果。"""

    path: Path
    units: List[Unit] = field(default_factory=list)
    problems: List[Problem] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.path.stem

    def all_lines(self):
        """(本, コマ, 台詞) の組を順番に取り出す。"""
        for unit in self.units:
            for panel in unit.panels:
                for line in panel.lines:
                    yield unit, panel, line
