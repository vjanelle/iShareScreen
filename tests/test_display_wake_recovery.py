"""Display wake must re-arm media even when the canvas size is unchanged."""
from __future__ import annotations

import struct
import types

import pytest

from isharescreen.proxy.protocol.enc1103 import StreamCipher
from isharescreen.proxy.protocol.negotiation import NegotiationKeys
from isharescreen.proxy.session import Session, SessionConfig


class _ControlSocket:
    def __init__(self):
        self.records = []

    def sendall(self, data):
        self.records.append(data)


def _layout(width=1920, height=1080, *, backing=None):
    bw, bh = backing if backing is not None else (width, height)
    payload = struct.pack(">HHHHH", 1, width, height, bw, bh)
    return (b"\x00\x00\x00\x01"
            + struct.pack(">HHHHiH", 0, 0, width, height, 0x451, len(payload))
            + payload)


def _session(codec):
    session = Session(SessionConfig(host="test", username="test", password=""))
    session._video_codec = codec
    sock = _ControlSocket()
    # Real record framing/encryption, with a second endpoint to inspect sends.
    session._negotiation = types.SimpleNamespace(
        sock=sock, cipher=StreamCipher(bytes(36), ecb_key=bytes(16)),
        keys=NegotiationKeys(*(bytes([i]) * 46 for i in range(1, 5))),
    )
    session._video_offer = b"video-offer"
    session._audio_offer = b"audio-offer"
    peer = StreamCipher(bytes(36), ecb_key=bytes(16))
    return session, sock, peer


def _messages(sock, peer):
    messages = []
    for record in sock.records:
        message = peer.decrypt_message(record[2:])
        assert message is not None
        messages.append(message)
    sock.records.clear()
    return messages


@pytest.mark.parametrize("codec", ["avc", "hevc"])
def test_wake_at_same_size_reoffers_existing_media(monkeypatch, codec):
    clock = [100.0]
    monkeypatch.setattr("isharescreen.proxy.session.time.monotonic", lambda: clock[0])
    session, sock, peer = _session(codec)
    session._handle_fbu(_layout())  # Initial layout confirmation.
    assert [m[0] for m in _messages(sock, peer)] == [0x03]

    clock[0] = 160.0  # Sleep/wake, with the same backing and scaled sizes.
    session._handle_fbu(_layout())

    messages = _messages(sock, peer)
    assert [m[0] for m in messages] == [0x03, 0x1C]
    offer = messages[1]
    assert offer[0x24:0x52] == bytes([1]) * 46
    assert b"video-offer" in offer and b"audio-offer" in offer
    assert session.canvas_dims == (1920, 1080)
    assert session._needs_post_layout_fir is True
    # A same-size wake must not wait for changed SPS/config that may never come.
    assert session._needs_param_harvest is False
    assert session._avc_needs_reconfig is False

    # A layout echo from the re-offer must not start a negotiation loop.
    session._handle_fbu(_layout())
    assert [m[0] for m in _messages(sock, peer)] == [0x03]

    clock[0] = 220.0  # A later sleep/wake still needs its own re-offer.
    session._handle_fbu(_layout())
    assert [m[0] for m in _messages(sock, peer)] == [0x03, 0x1C]


@pytest.mark.parametrize("codec", ["avc", "hevc"])
def test_real_resize_is_not_suppressed_by_wake_cooldown(monkeypatch, codec):
    monkeypatch.setattr("isharescreen.proxy.session.time.monotonic", lambda: 100.0)
    session, sock, peer = _session(codec)
    session._handle_fbu(_layout())
    _messages(sock, peer)
    session._handle_fbu(_layout())  # Same-size transition starts the cooldown.
    _messages(sock, peer)

    session._handle_fbu(_layout(1280, 720))

    assert [m[0] for m in _messages(sock, peer)] == [0x03, 0x1C]
    assert session.canvas_dims == (1280, 720)
    assert session._avc_needs_reconfig is (codec == "avc")
    assert session._needs_param_harvest is (codec == "hevc")


def test_sleep_layout_without_backing_does_not_consume_wake_recovery(monkeypatch):
    monkeypatch.setattr("isharescreen.proxy.session.time.monotonic", lambda: 100.0)
    session, sock, peer = _session("hevc")
    session._handle_fbu(_layout())
    _messages(sock, peer)

    session._handle_fbu(_layout(backing=(0, 0)))

    assert [m[0] for m in _messages(sock, peer)] == [0x03]
    assert session.canvas_dims == (1920, 1080)
    session._handle_fbu(_layout())
    assert [m[0] for m in _messages(sock, peer)] == [0x03, 0x1C]
