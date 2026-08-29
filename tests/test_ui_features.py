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

    def test_mlb_rgb_object_supported(self):
        self.assertIn('["r","g","b"].every', self.js)
        self.assertIn('rgbForOriginal', self.js)
        self.assertIn('{r:255,g:255,b:255}', self.js)

    def test_string_array_index_does_not_call_tolowercase_on_number(self):
        self.assertIn('String(path.at(-1)).toLowerCase()', self.js)

    def test_render_error_boundary_present(self):
        self.assertIn('Structured editor render failed:', self.js)

if __name__ == "__main__":
    unittest.main()
