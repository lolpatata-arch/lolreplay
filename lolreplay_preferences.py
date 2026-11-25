"""Validated local UI preferences; independent of recording configuration."""
OPTIONS = {
    'text_scale': (100, 110, 120),
    'high_contrast': (False, True),
    'strong_focus': (True, False),
    'large_targets': (False, True),
    'tile_size': ('normal', 'large', 'compact'),
    'startup_page': (0, 1, 2, 3),
    'single_click_play': (True, False),
    'video_click': (True, False),
    'loop_playback': (False, True),
    'playback_speed': (100, 50, 75, 125, 150, 200),
    'seek_seconds': (5, 2, 10, 15),
    'pause_in_background': (False, True),
    'keyboard_shortcuts': (True, False),
    'thumbnails': (True, False),
    'refresh_ms': (2500, 5000, 10000),
    'background_refresh': (False, True),
}
DEFAULTS = {key: values[0] for key, values in OPTIONS.items()}


def validated(raw):
    if not isinstance(raw, dict): raw = {}
    result = DEFAULTS.copy()
    for key, choices in OPTIONS.items():
        value = raw.get(key)
        if any(type(value) is type(choice) and value == choice for choice in choices):
            result[key] = value
    return result


def merge_ui(data, prefs):
    return {**(data if isinstance(data, dict) else {}), 'preferences': validated(prefs)}
