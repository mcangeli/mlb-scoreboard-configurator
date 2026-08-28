import unittest
from pathlib import Path

class UiFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.js = (cls.root / "mlb_scoreboard_configurator" / "static" / "app.js").read_text()
        cls.css = (cls.root / "mlb_scoreboard_configurator" / "static" / "app.css").read_text()

    def test_two_dimensional_color_picker_present(self):
        self.assertIn('className="svPicker"', self.js)
        self.assertIn('pointerdown', self.js)
        self.assertIn('className="hueSlider"', self.js)

    def test_add_item_ui_present(self):
        self.assertIn('＋ Add item', self.js)
        self.assertIn('＋ Add list item', self.js)
        self.assertIn('RGB color', self.js)

    def test_picker_css_present(self):
        self.assertIn('.svPicker{', self.css)
        self.assertIn('.addItemPanel{', self.css)

if __name__ == "__main__":
    unittest.main()
