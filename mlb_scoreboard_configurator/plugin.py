"""Bullpen registration shim.

The configurator is a management service rather than a visible rotation screen.
Keeping a valid Bullpen entry point makes it install like other v9 plugins while
the Flask process remains independently available through systemd.
"""
try:
    from bullpen.api import UpdateStatus
except Exception:  # Allows package tooling/tests away from the scoreboard.
    UpdateStatus = None

class Config:
    def __init__(self, config):
        self.config = config
        self.plugin_config = getattr(config, "plugin_config", {}) or {}

class Data:
    def __init__(self, config):
        self.config = config
    def update(self):
        return UpdateStatus.DEFERRED if UpdateStatus is not None else None

class Renderer:
    def __init__(self, config, coordinates, colors):
        self.config = config
        self.coordinates = coordinates
        self.colors = colors
    def render(self, data, canvas, graphics, scroll_position):
        return None
    def wait_time(self):
        return 1.0
    def can_render(self, data):
        return False
    def reset(self):
        return None

def load():
    return Config, Data, Renderer
