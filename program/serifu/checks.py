"""読み取った台本をチェックして、警告を作る部分。"""
from __future__ import annotations

from collections import Counter
from typing import List

from .models import Problem, Script
from .settings import Settings


def run_checks(script: Script, settings: Settings) -> List[Problem]:
    problems: List[Problem] = []

    if not script.units:
        problems.append(Problem(
            "読み取れない箇所",
            "本が1つも見つかりません。「### 01「タイトル」」の見出しと「コマ｜絵｜台詞・音」の表があるか確かめてください",
        ))

    # 本番号の重複
    counts = Counter(u.number for u in script.units if u.number)
    for number, n in counts.items():
        if n > 1:
            problems.append(Problem("本番号", f"本番号「{number}」が{n}回出てきます（重複）"))

    for unit in script.units:
        # コマ数
        if settings.panels_per_unit and unit.panels and len(unit.panels) != settings.panels_per_unit:
            problems.append(Problem(
                "コマ数",
                f"コマが{len(unit.panels)}つあります（{settings.panels_per_unit}コマではありません）",
                line_no=unit.source_line, unit=unit.label,
            ))

        # コマ番号の重複・飛び・順番
        numbers = [p.number for p in unit.panels if p.number is not None]
        dup = sorted(n for n, c in Counter(numbers).items() if c > 1)
        for n in dup:
            problems.append(Problem("コマ番号", f"コマ番号「{n}」が重複しています",
                                    line_no=unit.source_line, unit=unit.label))
        if numbers:
            expected = range(1, max(numbers) + 1)
            missing = [n for n in expected if n not in numbers]
            if missing:
                problems.append(Problem(
                    "コマ番号",
                    "コマ番号が飛んでいます（" + "・".join(map(str, missing)) + " がありません）",
                    line_no=unit.source_line, unit=unit.label,
                ))
            if not dup and numbers != sorted(numbers):
                problems.append(Problem(
                    "コマ番号",
                    "コマ番号の順番が入れ替わっています（" + "→".join(map(str, numbers)) + "）",
                    line_no=unit.source_line, unit=unit.label,
                ))

        # 長すぎる台詞
        if settings.max_chars:
            for panel in unit.panels:
                for line in panel.lines:
                    if line.is_se and not settings.check_se_length:
                        continue
                    if line.char_count > settings.max_chars:
                        problems.append(Problem(
                            "長い台詞",
                            f"{line.char_count}文字あります（上限 {settings.max_chars}文字）",
                            line_no=panel.source_line, unit=unit.label, panel=panel.label,
                            content=line.raw,
                        ))

    return problems
