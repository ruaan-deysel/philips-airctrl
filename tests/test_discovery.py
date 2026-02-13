"""Tests for the discovery module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from philips_airctrl.discovery import DeviceDiscovery
from philips_airctrl.models import DeviceInfo


class TestDeviceDiscovery:
    def test_init(self):
        discovery = DeviceDiscovery()
        assert discovery.timeout == 5.0

    def test_init_custom_timeout(self):
        discovery = DeviceDiscovery(timeout=10.0)
        assert discovery.timeout == 10.0

    def test_get_network_ranges(self):
        mock_interfaces = ["lo", "eth0"]
        mock_addrs = {2: [{"addr": "192.168.1.100", "netmask": "255.255.255.0"}]}

        with (
            patch("philips_airctrl.discovery.netifaces.interfaces", return_value=mock_interfaces),
            patch("philips_airctrl.discovery.netifaces.ifaddresses", return_value=mock_addrs),
            patch("philips_airctrl.discovery.netifaces.AF_INET", 2),
        ):
            discovery = DeviceDiscovery()
            ranges = discovery.get_network_ranges()
            assert "192.168.1.0/24" in ranges

    def test_get_network_ranges_skips_loopback(self):
        with (
            patch("philips_airctrl.discovery.netifaces.interfaces", return_value=["lo"]),
            patch("philips_airctrl.discovery.netifaces.ifaddresses", return_value={}),
            patch("philips_airctrl.discovery.netifaces.AF_INET", 2),
        ):
            discovery = DeviceDiscovery()
            ranges = discovery.get_network_ranges()
            assert ranges == []

    def test_get_network_ranges_skips_127(self):
        mock_addrs = {2: [{"addr": "127.0.0.1", "netmask": "255.0.0.0"}]}

        with (
            patch("philips_airctrl.discovery.netifaces.interfaces", return_value=["lo0"]),
            patch("philips_airctrl.discovery.netifaces.ifaddresses", return_value=mock_addrs),
            patch("philips_airctrl.discovery.netifaces.AF_INET", 2),
        ):
            discovery = DeviceDiscovery()
            ranges = discovery.get_network_ranges()
            assert ranges == []

    def test_get_network_ranges_no_ipv4(self):
        with (
            patch("philips_airctrl.discovery.netifaces.interfaces", return_value=["eth0"]),
            patch("philips_airctrl.discovery.netifaces.ifaddresses", return_value={}),
            patch("philips_airctrl.discovery.netifaces.AF_INET", 2),
        ):
            discovery = DeviceDiscovery()
            ranges = discovery.get_network_ranges()
            assert ranges == []

    def test_get_network_ranges_invalid_network(self):
        mock_addrs = {2: [{"addr": "invalid", "netmask": "invalid"}]}

        with (
            patch("philips_airctrl.discovery.netifaces.interfaces", return_value=["eth0"]),
            patch("philips_airctrl.discovery.netifaces.ifaddresses", return_value=mock_addrs),
            patch("philips_airctrl.discovery.netifaces.AF_INET", 2),
        ):
            discovery = DeviceDiscovery()
            ranges = discovery.get_network_ranges()
            assert ranges == []

    def test_get_network_ranges_exception(self):
        with patch("philips_airctrl.discovery.netifaces.interfaces", side_effect=Exception("fail")):
            discovery = DeviceDiscovery()
            ranges = discovery.get_network_ranges()
            assert ranges == ["192.168.1.0/24", "192.168.0.0/24", "10.0.0.0/24"]

    def test_get_network_ranges_missing_addr(self):
        mock_addrs = {2: [{"netmask": "255.255.255.0"}]}

        with (
            patch("philips_airctrl.discovery.netifaces.interfaces", return_value=["eth0"]),
            patch("philips_airctrl.discovery.netifaces.ifaddresses", return_value=mock_addrs),
            patch("philips_airctrl.discovery.netifaces.AF_INET", 2),
        ):
            discovery = DeviceDiscovery()
            ranges = discovery.get_network_ranges()
            assert ranges == []

    @pytest.mark.asyncio
    async def test_scan_ip_port_not_reachable(self):
        with patch("philips_airctrl.discovery.socket.socket") as mock_sock_class:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 1  # Port not reachable
            mock_sock.__enter__ = MagicMock(return_value=mock_sock)
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_sock_class.return_value = mock_sock

            discovery = DeviceDiscovery()
            result = await discovery.scan_ip("192.168.1.50")
            assert result is None

    @pytest.mark.asyncio
    async def test_scan_ip_socket_exception(self):
        with patch("philips_airctrl.discovery.socket.socket") as mock_sock_class:
            mock_sock = MagicMock()
            mock_sock.connect_ex.side_effect = OSError("fail")
            mock_sock.__enter__ = MagicMock(return_value=mock_sock)
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_sock_class.return_value = mock_sock

            discovery = DeviceDiscovery()
            result = await discovery.scan_ip("192.168.1.50")
            assert result is None

    @pytest.mark.asyncio
    async def test_scan_ip_success(self):
        with (
            patch("philips_airctrl.discovery.socket.socket") as mock_sock_class,
            patch("philips_airctrl.discovery.Client.create") as mock_create,
        ):
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0
            mock_sock.__enter__ = MagicMock(return_value=mock_sock)
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_sock_class.return_value = mock_sock

            mock_client = AsyncMock()
            mock_client.get_status.return_value = (
                {
                    "D01S05": "AC4220",
                    "D01S03": "Living Room",
                    "DeviceId": "abc",
                    "ProductId": "prod",
                    "D01S12": "1.0",
                    "WifiVersion": "2.0",
                    "D01S0D": "SN123",
                },
                60,
            )
            mock_create.return_value = mock_client

            discovery = DeviceDiscovery(timeout=5.0)
            result = await discovery.scan_ip("192.168.1.50")

            assert result is not None
            assert isinstance(result, DeviceInfo)
            assert result.ip == "192.168.1.50"
            assert result.model == "AC4220"
            assert result.name == "Living Room"
            assert result.reachable is True
            mock_client.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_ip_timeout(self):
        with (
            patch("philips_airctrl.discovery.socket.socket") as mock_sock_class,
            patch(
                "philips_airctrl.discovery.Client.create",
                side_effect=TimeoutError(),
            ),
        ):
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0
            mock_sock.__enter__ = MagicMock(return_value=mock_sock)
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_sock_class.return_value = mock_sock

            discovery = DeviceDiscovery(timeout=0.1)
            result = await discovery.scan_ip("192.168.1.50")
            assert result is None

    @pytest.mark.asyncio
    async def test_scan_ip_connection_error(self):
        with (
            patch("philips_airctrl.discovery.socket.socket") as mock_sock_class,
            patch(
                "philips_airctrl.discovery.Client.create",
                side_effect=ConnectionError("fail"),
            ),
        ):
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0
            mock_sock.__enter__ = MagicMock(return_value=mock_sock)
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_sock_class.return_value = mock_sock

            discovery = DeviceDiscovery(timeout=0.1)
            result = await discovery.scan_ip("192.168.1.50")
            assert result is None

    @pytest.mark.asyncio
    async def test_scan_ip_outer_exception(self):
        with patch("philips_airctrl.discovery.socket.socket", side_effect=OSError("fail")):
            discovery = DeviceDiscovery()
            result = await discovery.scan_ip("192.168.1.50")
            assert result is None

    @pytest.mark.asyncio
    async def test_discover_devices(self):
        device = DeviceInfo(ip="192.168.1.50", reachable=True)

        with patch.object(DeviceDiscovery, "scan_ip") as mock_scan:
            # Return device for first IP, None for rest
            async def scan_side_effect(ip):
                if ip == "192.168.1.1":
                    return device
                return None

            mock_scan.side_effect = scan_side_effect

            discovery = DeviceDiscovery()
            devices = await discovery.discover_devices(["192.168.1.0/30"])

            assert len(devices) == 1
            assert devices[0].ip == "192.168.1.50"

    @pytest.mark.asyncio
    async def test_discover_devices_uses_default_networks(self):
        with (
            patch.object(DeviceDiscovery, "get_network_ranges", return_value=["192.168.1.0/30"]),
            patch.object(DeviceDiscovery, "scan_ip", return_value=None),
        ):
            discovery = DeviceDiscovery()
            devices = await discovery.discover_devices()
            assert devices == []

    @pytest.mark.asyncio
    async def test_discover_devices_skips_large_networks(self):
        with patch.object(DeviceDiscovery, "scan_ip", return_value=None) as mock_scan:
            discovery = DeviceDiscovery()
            devices = await discovery.discover_devices(["10.0.0.0/8"])  # Too large
            assert devices == []
            mock_scan.assert_not_called()

    @pytest.mark.asyncio
    async def test_discover_devices_handles_scan_exception(self):
        async def scan_raises(ip):
            raise Exception("scan failed")

        with patch.object(DeviceDiscovery, "scan_ip", side_effect=scan_raises):
            discovery = DeviceDiscovery()
            devices = await discovery.discover_devices(["192.168.1.0/30"])
            assert devices == []

    @pytest.mark.asyncio
    async def test_discover_devices_invalid_network(self):
        with patch.object(DeviceDiscovery, "scan_ip", return_value=None) as mock_scan:
            discovery = DeviceDiscovery()
            devices = await discovery.discover_devices(["not-a-network"])
            assert devices == []
            mock_scan.assert_not_called()

    @pytest.mark.asyncio
    async def test_discover_single_network(self):
        with patch.object(DeviceDiscovery, "discover_devices", new_callable=AsyncMock) as mock_dd:
            mock_dd.return_value = []
            discovery = DeviceDiscovery()
            await discovery.discover_single_network("192.168.1.0/24")
            mock_dd.assert_called_once_with(["192.168.1.0/24"])
