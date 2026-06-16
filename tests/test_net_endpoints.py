import pytest

from main.domain.models.node_info import NodeInfo
from main.infrastructure.net.endpoints import (
    format_host_port,
    hosts_match,
    parse_host_port,
    parse_peers_string,
    peer_matches_hello,
    resolve_bind_host,
)
from main.domain.models.payloads import HelloPayload


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


def test_peer_matches_hello_by_node_id_in_config():
    peer = NodeInfo(host="127.0.0.1", port=8002, node_id="node2")
    hello = HelloPayload(node_id="node2", public_key="aGVsbG8=", listen_port=8002)
    assert peer_matches_hello(peer, "10.0.0.5", 45678, hello)


def test_peer_matches_hello_docker_hostname():
    peer = NodeInfo(host="node3", port=8003)
    hello = HelloPayload(node_id="node3", public_key="aGVsbG8=", listen_port=8003)
    assert peer_matches_hello(peer, "::ffff:172.21.0.4", 57836, hello)


def test_peer_matches_hello_rejects_unknown():
    peer = NodeInfo(host="node3", port=8003)
    hello = HelloPayload(node_id="intruder", public_key="aGVsbG8=", listen_port=8003)
    assert not peer_matches_hello(peer, "::ffff:172.21.0.4", 57836, hello)
