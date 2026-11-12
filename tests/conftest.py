"""Keep one Qt application alive while native widget tests exchange signals."""
import os

import pytest


@pytest.fixture(scope="session")
def qt_application():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


@pytest.fixture(autouse=True)
def keep_native_test_application_alive(request):
    if request.module.__name__.split(".")[-1].startswith("test_native_"):
        request.getfixturevalue("qt_application")
