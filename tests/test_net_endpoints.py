import pytest

from main.domain.models.node_info import NodeInfo
from main.infrastructure.net.endpoints import (
    format_host_port,
    hosts_match,
    parse_host_port,
    parse_peers_string,
    resolve_bind_host,
)


def test_parse_host_port_ipv4():
    assert parse_host_port("127.0.0.1:8001") == ("127.0.0.1", 8001)


def test_parse_host_port_ipv6_bracketed():
    assert parse_host_port("[::1]:8002") == ("::1", 8002)


def test_parse_peers_string_mixed():
    peers = parse_peers_string("127.0.0.1:8001,[::1]:8002,node1:8003")
    assert peers == [
        NodeInfo(host="127.0.0.1", port=8001),
        NodeInfo(host="::1", port=8002),
        NodeInfo(host="node1", port=8003),
    ]


def test_hosts_match_ipv4_mapped():
    assert hosts_match("127.0.0.1", "::ffff:127.0.0.1")


def test_hosts_match_ipv6():
    assert hosts_match("::1", "[::1]")


def test_format_host_port_ipv6():
    assert format_host_port("::1", 9081) == "[::1]:9081"


def test_resolve_bind_host_auto():
    assert resolve_bind_host("auto") is None
    assert resolve_bind_host("") is None
    assert resolve_bind_host("0.0.0.0") == "0.0.0.0"
    assert resolve_bind_host("::") == "::"


def test_parse_host_port_invalid():
    with pytest.raises(ValueError):
        parse_host_port("not-an-endpoint")
