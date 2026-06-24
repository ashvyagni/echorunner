from src.fonts import _CHARS, _blocky_render

def test_blocky_font_integrity():
    for ch in _CHARS:
        surf = _blocky_render(ch, 16, (255, 255, 255))
        assert surf.get_width() > 0 and surf.get_height() > 0, f"empty surface for '{ch}'"
