from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_learner_profile_exposes_audience_experience_and_devices():
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="learnerAudience"' in html
    assert 'id="experience"' in html
    assert 'class="device-fieldset"' in html
    assert 'aria-live="polite"' in html


def test_profile_preview_is_device_aware_and_mobile_safe():
    js = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert "refreshProfilePreview" in js
    assert "device_paths" in js
    assert ".profile-preview" in css
    assert "@media(max-width:420px)" in css
    assert "prefers-reduced-motion" in css
