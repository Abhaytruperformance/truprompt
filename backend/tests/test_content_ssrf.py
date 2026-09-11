"""Invariant: no private/loopback/link-local/reserved address is ever
fetched by the content-extraction feature, including via DNS rebinding
(a hostname that resolves safely at pre-check time but connects to an
unsafe address moments later)."""

import ipaddress

import pytest

from app.services.content_extraction_service import (
    UnsafeUrl,
    _assert_safe_host,
    _assert_safe_peer,
    _is_unsafe_ip,
    extract_from_url,
)


@pytest.mark.parametrize("ip", [
    "127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.1.1", "0.0.0.0", "::1",
])
def test_is_unsafe_ip_flags_private_and_special_ranges(ip):
    assert _is_unsafe_ip(ipaddress.ip_address(ip)) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34"])
def test_is_unsafe_ip_allows_public_addresses(ip):
    assert _is_unsafe_ip(ipaddress.ip_address(ip)) is False


def test_extract_from_url_rejects_a_loopback_hostname_up_front():
    with pytest.raises(UnsafeUrl):
        extract_from_url("http://127.0.0.1/")


def test_extract_from_url_rejects_a_private_hostname_up_front():
    with pytest.raises(UnsafeUrl):
        extract_from_url("http://localhost/")


def test_assert_safe_peer_catches_dns_rebinding():
    """Simulates the exact attack _assert_safe_peer exists to close: a
    hostname passes the pre-connect DNS check (_assert_safe_host would see a
    public IP), but by the time the HTTP client actually connects, the
    resolved/connected address is unsafe. This directly exercises the
    post-connect check without needing a real rebinding DNS server."""

    class FakeNetworkStream:
        def get_extra_info(self, key):
            if key == "server_addr":
                return ("127.0.0.1", 443)  # the unsafe address it actually connected to
            return None

    class FakeResponse:
        extensions = {"network_stream": FakeNetworkStream()}

    with pytest.raises(UnsafeUrl):
        _assert_safe_peer(FakeResponse(), "attacker-controlled-hostname.example")


def test_assert_safe_peer_allows_a_genuinely_public_address():
    class FakeNetworkStream:
        def get_extra_info(self, key):
            if key == "server_addr":
                return ("93.184.216.34", 443)
            return None

    class FakeResponse:
        extensions = {"network_stream": FakeNetworkStream()}

    _assert_safe_peer(FakeResponse(), "example.com")  # must not raise
