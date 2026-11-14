from isharescreen.frontend.desktop import app


def test_viewer_is_created_without_requesting_focus(monkeypatch):
    hints = []
    monkeypatch.setattr(app.glfw, "init", lambda: True)
    monkeypatch.setattr(app.glfw, "window_hint", lambda hint, value: hints.append((hint, value)))
    sentinel = object()
    def create_canvas(**kwargs):
        assert (app.glfw.FOCUSED, False) in hints
        assert (app.glfw.FOCUS_ON_SHOW, False) in hints
        return sentinel

    monkeypatch.setattr(app, "RenderCanvas", create_canvas)

    assert app._create_viewer_window(title="Viewer", size=(800, 600)) is sentinel
    assert hints[-2:] == [(app.glfw.FOCUSED, True), (app.glfw.FOCUS_ON_SHOW, True)]
