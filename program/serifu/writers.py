"""Excel・テキストファイルを書き出す部分。"""
from __future__ import annotations

from pathlib import Path
from typing import List

from .models import Problem, Script
from .settings import Settings

NEWLINE = "\r\n"  # Windows のメモ帳で見やすい改行

# Excel の色
COLOR_HEADER = "305496"
COLOR_SE = "FCE4D6"  # 効果音の行（薄いオレンジ）
COLOR_SE_FONT = "9C5700"
COLOR_UNIT_BORDER = "8EA9DB"


def write_excel(script: Script, problems: List[Problem], path: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = Workbook()
    ws = wb.active
    ws.title = "セリフ一覧"

    headers = ["本番号", "本タイトル", "コマ", "話者", "種類", "テキスト", "文字数", "絵（参考用）"]
    widths = [8, 22, 6, 12, 16, 50, 8, 60]
    ws.append(headers)
    for col, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = w
        c = ws.cell(row=1, column=col)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=COLOR_HEADER)
        c.alignment = Alignment(horizontal="center", vertical="center")

    se_fill = PatternFill("solid", fgColor=COLOR_SE)
    se_font = Font(color=COLOR_SE_FONT, italic=True)
    top_line = Border(top=Side(style="medium", color=COLOR_UNIT_BORDER))
    wrap = Alignment(wrap_text=True, vertical="top")
    top = Alignment(vertical="top")
    center = Alignment(horizontal="center", vertical="top")

    prev_unit = None
    for unit, panel, line in script.all_lines():
        ws.append([
            unit.number, unit.title, panel.number if panel.number is not None else panel.number_raw,
            line.speaker, line.kind, line.text, line.char_count, panel.picture,
        ])
        r = ws.max_row
        ws.cell(row=r, column=1).number_format = "@"  # 「01」の0が消えないように文字として扱う
        for col in range(1, len(headers) + 1):
            c = ws.cell(row=r, column=col)
            c.alignment = wrap if col in (6, 8) else (center if col in (1, 3, 7) else top)
            if line.is_se:
                c.fill = se_fill
                c.font = se_font
            if prev_unit is not None and unit is not prev_unit:
                c.border = top_line
        prev_unit = unit

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{ws.cell(row=1, column=len(headers)).column_letter}{ws.max_row}"

    # 警告のシート
    wp = wb.create_sheet("警告")
    wp.append(["種類", "行", "本", "コマ", "内容", "問題の箇所"])
    for col, w in enumerate([16, 6, 26, 6, 70, 50], start=1):
        c = wp.cell(row=1, column=col)
        wp.column_dimensions[c.column_letter].width = w
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=COLOR_HEADER)
    if problems:
        for p in problems:
            wp.append([p.category, p.line_no or "", p.unit, p.panel, p.message, p.content])
            for col in range(1, 7):
                wp.cell(row=wp.max_row, column=col).alignment = wrap
    else:
        wp.append(["警告はありません"])
    wp.freeze_panes = "A2"

    # 凡例
    wl = wb.create_sheet("見かた")
    notes = [
        ["セリフ一覧の見かた"],
        [""],
        ["オレンジ色の行", "効果音（描き文字）。写植しない場合が多いので色を変えています"],
        ["白い行", "写植する台詞（台詞・心の声・モノローグなど）"],
        ["本の区切り", "本が変わるところに青い線を引いています"],
        ["文字数", "空白は数えません。「……」は2文字と数えます"],
        ["絞り込み", "1行目の▼ボタンで、話者や種類ごとに絞り込めます"],
        ["警告", "「警告」シートに、チェックで見つかった問題をまとめています"],
    ]
    for row in notes:
        wl.append(row)
    wl["A1"].font = Font(bold=True, size=14)
    wl["A3"].fill = se_fill
    wl["A3"].font = se_font
    wl.column_dimensions["A"].width = 18
    wl.column_dimensions["B"].width = 70

    wb.save(path)


def speaker_label(line) -> str:
    """台本に書かれていたとおりの話者表記（例：結衣（心）、SE（奥））。"""
    raw = line.raw.replace("**", "")
    cut = min((raw.index(q) for q in "「『" if q in raw), default=len(raw))
    return raw[:cut].strip() or line.speaker


def build_text(script: Script, settings: Settings) -> str:
    out: List[str] = []
    se_note = "含める" if settings.text_include_se else "含めない"
    out.append(f"{script.name}　セリフ一覧（効果音：{se_note}）")
    out.append("")

    for unit in script.units:
        out.append("━" * 20)
        out.append(unit.label)
        out.append("━" * 20)
        wrote_any = False
        for panel in unit.panels:
            lines = [l for l in panel.lines if settings.text_include_se or not l.is_se]
            if not lines and not settings.text_show_empty_panels:
                continue
            out.append(f"【{panel.label}コマ】")
            if not lines:
                out.append("（台詞なし）")
            for line in lines:
                if settings.text_show_speaker:
                    out.append(f"{speaker_label(line)}：{line.text}")
                elif line.is_se:
                    out.append(f"［効果音］{line.text}")
                else:
                    out.append(line.text)
            out.append("")
            wrote_any = True
        if not wrote_any:
            out.append("（台詞なし）")
            out.append("")
        out.append("")
    return NEWLINE.join(out).rstrip() + NEWLINE


def write_text(script: Script, settings: Settings, path: Path) -> None:
    # BOM 付き UTF-8：メモ帳でも古いソフトでも文字化けしにくい
    path.write_bytes(build_text(script, settings).encode("utf-8-sig"))


def build_problems_text(script: Script, problems: List[Problem]) -> str:
    out = [f"{script.name}　警告一覧", ""]
    if not problems:
        out.append("警告はありません。")
    else:
        out.append(f"警告が {len(problems)} 件あります。")
        out.append("")
        for p in problems:
            out.append("・" + p.to_text())
    return NEWLINE.join(out) + NEWLINE


def write_problems(script: Script, problems: List[Problem], path: Path) -> None:
    path.write_bytes(build_problems_text(script, problems).encode("utf-8-sig"))
