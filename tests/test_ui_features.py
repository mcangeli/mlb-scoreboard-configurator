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


    def test_rgb_picker_does_not_map_raw_object_value(self):
        start = self.js.index('if(isRgb(value)){')
        end = self.js.index('if(typeof value==="boolean"){', start)
        block = self.js[start:end]
        self.assertNotIn('value.map(', block)
        self.assertIn('const initialRgb=rgbArray(value);', block)


    def test_system_settings_page_present(self):
        template=(self.root / "mlb_scoreboard_configurator" / "templates" / "index.html").read_text()
        self.assertIn('id="systemSettingsPage"', template)
        self.assertIn('id="piHostname"', template)
        self.assertIn('id="configAuthUsername"', template)
        self.assertIn('id="configAuthPassword"', template)
        self.assertIn('/api/system/auth', self.js)
        self.assertIn('/api/system/hostname', self.js)


    def test_system_page_uses_same_navigation_model(self):
        template=(self.root / "mlb_scoreboard_configurator" / "templates" / "index.html").read_text()
        self.assertIn('id="systemSettingsNav" class="nav sideNavButton" data-view="system"', template)
        self.assertIn('const editorPage=$("#editorPage");', self.js)
        self.assertIn('editorPage?.classList.remove("hidden");', self.js)
        self.assertIn('if(name==="system")', self.js)
        self.assertNotIn('function showSystemSettings()', self.js)
        self.assertNotIn('function showEditorPage()', self.js)

    def test_service_restart_remains_service_action(self):
        template=(self.root / "mlb_scoreboard_configurator" / "templates" / "index.html").read_text()
        self.assertIn('data-service="restart"', template)


    def test_plugins_page_present(self):
        template=(self.root / "mlb_scoreboard_configurator" / "templates" / "index.html").read_text()
        self.assertIn('id="pluginsNav"', template)
        self.assertIn('data-view="plugins"', template)
        self.assertIn('id="pluginsPage"', template)
        self.assertIn('id="pluginGithubUrl"', template)
        self.assertIn('id="installPluginBtn"', template)
        self.assertIn('/api/plugins/install', self.js)
        self.assertIn('function refreshPlugins()', self.js)

    def test_plugin_update_uninstall_controls(self):
        template=(self.root / "mlb_scoreboard_configurator" / "templates" / "index.html").read_text()
        self.assertIn('id="removePluginConfig"',template)
        self.assertIn('/api/plugins/update',self.js)
        self.assertIn('/api/plugins/uninstall',self.js)
        self.assertIn('data-plugin-update',self.js)
        self.assertIn('data-plugin-uninstall',self.js)


    def test_plugin_uninstall_screen_cleanup_ui(self):
        template=(self.root / "mlb_scoreboard_configurator" / "templates" / "index.html").read_text()
        self.assertIn("rotation.screens", template)
        self.assertIn("removed_screens", self.js)

if __name__ == "__main__":
    unittest.main()
