"""A decoded software frame alone does not prove a hardware device bound."""
from types import SimpleNamespace

import av
import pytest

from isharescreen.proxy.media import hevc, hwcaps


@pytest.mark.parametrize("bound", [False, True])
def test_probe_requires_a_bound_hardware_context(monkeypatch, bound):
    # PyAV can accept HWAccel for a device absent from the linked FFmpeg,
    # ignore it, and decode in software despite allow_software_fallback=False.
    class Context:
        is_hwaccel = bound

        def decode(self, packet):
            return [] if packet is None else [SimpleNamespace(format=SimpleNamespace(name="yuv444p"))]

    monkeypatch.setattr(av, "CodecContext", SimpleNamespace(create=lambda *a, **kw: Context()))
    assert hwcaps._probe_one("vaapi") is bound


def test_linux_vulkan_is_probed_and_available_to_decoder(monkeypatch):
    monkeypatch.setattr(hevc.sys, "platform", "linux")
    assert "vulkan" in hevc._platform_hwaccels()
    assert "vulkan" in hwcaps._PROBE_HWACCELS.get("linux", hwcaps._PROBE_HWACCELS["*"])
