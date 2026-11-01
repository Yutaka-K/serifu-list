"""動作確認用のテスト。ツールのフォルダで次のように実行します：
    python -m unittest discover tests
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "program"))

from serifu.checks import run_checks  # noqa: E402
from serifu.parsers import get_parser  # noqa: E402
from serifu.settings import Settings  # noqa: E402
from serifu.writers import build_text  # noqa: E402


def load(name):
    path = ROOT / name
    settings = Settings()
    script = get_parser("4コマ")(path.read_text(encoding="utf-8"), path, settings)
    return script, script.problems + run_checks(script, settings), settings


class SampleTest(unittest.TestCase):
    def test_sample_script(self):
        script, problems, _ = load("第1話_台本.md")
        self.assertEqual(len(script.units), 21)
        self.assertTrue(all(len(u.panels) == 4 for u in script.units))
        lines = [l for _, _, l in script.all_lines()]
        self.assertEqual(len(lines), 60)
        self.assertEqual(sum(l.is_se for l in lines), 13)
        self.assertEqual(problems, [])
        first = lines[0]
        self.assertEqual((first.speaker, first.kind, first.text), ("結衣", "心の声", "バイト終わりは、さすがにしんどい……"))
        kinds = {l.kind for l in lines}
        self.assertTrue({"台詞", "心の声", "モノローグ", "寝言", "効果音", "効果音（奥）", "効果音（息）"} <= kinds)


class WarningTest(unittest.TestCase):
    def setUp(self):
        self.script, self.problems, self.settings = load("tests/data/警告テスト用_台本.md")
        self.cats = [p.category for p in self.problems]

    def test_units(self):
        self.assertEqual([u.number for u in self.script.units], ["01", "02", "03"])  # 関係ない表は読まない

    def test_kinds(self):
        u1 = self.script.units[0]
        self.assertEqual(u1.panels[1].lines[0].kind, "電話")
        self.assertEqual(u1.panels[1].lines[1].kind, "効果音（遠く）")
        u3 = self.script.units[2]
        self.assertEqual(u3.panels[2].number, 3)
        self.assertEqual(u3.panels[2].lines[0].speaker, "太郎")

    def test_slash_inside_quotes(self):
        self.assertEqual(self.script.units[1].panels[1].lines[0].text, "『／』は区切りではありません")

    def test_warnings(self):
        msgs = "\n".join(p.to_text() for p in self.problems)
        self.assertIn("コマが3つあります", msgs)
        self.assertIn("コマ番号「2」が重複", msgs)
        self.assertIn("3 がありません", msgs)
        self.assertIn("上限 30文字", msgs)
        self.assertIn("かぎかっこ）が見つかりません", msgs)
        self.assertIn("話者名が書かれていません", msgs)
        self.assertIn("閉じかっこ", msgs)
        self.assertIn("列の数", msgs)

    def test_text_switch(self):
        self.settings.text_include_se = False
        self.assertNotIn("プルル", build_text(self.script, self.settings))
        self.settings.text_include_se = True
        self.assertIn("プルル", build_text(self.script, self.settings))
        self.settings.text_show_speaker = True
        self.assertIn("太郎（電話）：もしもし", build_text(self.script, self.settings))


if __name__ == "__main__":
    unittest.main()
