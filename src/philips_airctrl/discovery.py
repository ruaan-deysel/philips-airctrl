"""Device discovery functionality for Philips air purifiers."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket

import netifaces

from philips_airctrl.coap.client import Client
from philips_airctrl.models import DeviceInfo

logger = logging.getLogger(__name__)


class DeviceDiscovery:
    """Discover Philips air purifier devices on the network."""

    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout

    def get_network_ranges(self) -> list[str]:
        """Get all local network ranges to scan."""
        networks: list[str] = []

        try:
            interfaces = netifaces.interfaces()

            for interface in interfaces:
                if interface.startswith("lo"):
                    continue

                addrs = netifaces.ifaddresses(interface)

                if netifaces.AF_INET in addrs:
                    for addr_info in addrs[netifaces.AF_INET]:
                        ip = addr_info.get("addr")
                        netmask = addr_info.get("netmask")

                        if ip and netmask and not ip.startswith("127."):
                            try:
                                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                                networks.append(str(network))
                            except (ipaddress.AddressValueError, ValueError):
                                continue

        except Exception as e:
            logger.warning("Error getting network interfaces: %s", e)
            networks = ["192.168.1.0/24", "192.168.0.0/24", "10.0.0.0/24"]

        return networks

    async def scan_ip(self, ip: str) -> DeviceInfo | None:
        """Scan a single IP address for a Philips air purifier."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            try:
                result = sock.connect_ex((ip, 5683))
                sock.close()

                if result != 0:
                    return None
            except Exception:
                sock.close()
                return None

            try:
                client = await asyncio.wait_for(
                    Client.create(host=ip, port=5683),
                    timeout=self.timeout,
                )

                try:
                    status, _ = await asyncio.wait_for(
                        client.get_status(),
                        timeout=self.timeout,
                    )

                    device_info = DeviceInfo(
                        ip=ip,
                        reachable=True,
                        status=status,
                        model=status.get("D01S05", "Unknown"),
                        name=status.get("D01S03", "Unknown"),
                        device_id=status.get("DeviceId"),
                        product_id=status.get("ProductId"),
                        firmware_version=status.get("D01S12"),
                        wifi_version=status.get("WifiVersion"),
                        serial_number=status.get("D01S0D"),
                    )

                    logger.info("Found Philips air purifier at %s: %s", ip, device_info.model)
                    return device_info

                finally:
                    await client.shutdown()

            except TimeoutError:
                logger.debug("Timeout connecting to %s", ip)
                return None
            except Exception as e:
                logger.debug("Error connecting to %s: %s", ip, e)
                return None

        except Exception as e:
            logger.debug("Error scanning %s: %s", ip, e)
            return None

    async def discover_devices(self, networks: list[str] | None = None) -> list[DeviceInfo]:
        """Discover all Philips air purifier devices on the network."""
        if networks is None:
            networks = self.get_network_ranges()

        logger.info("Scanning networks: %s", networks)

        ips_to_scan: list[str] = []
        for network_str in networks:
            try:
                network = ipaddress.IPv4Network(network_str, strict=False)
                if network.prefixlen < 16:
                    logger.warning("Skipping large network %s (prefix < 16)", network_str)
                    continue

                for ip in network.hosts():
                    ips_to_scan.append(str(ip))

            except ipaddress.AddressValueError:
                logger.warning("Invalid network: %s", network_str)
                continue

        logger.info("Scanning %d IP addresses...", len(ips_to_scan))

        semaphore = asyncio.Semaphore(20)

        async def scan_with_semaphore(ip: str) -> DeviceInfo | None:
            async with semaphore:
                return await self.scan_ip(ip)

        tasks = [scan_with_semaphore(ip) for ip in ips_to_scan]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        devices: list[DeviceInfo] = []
        for result in results:
            if isinstance(result, DeviceInfo):
                devices.append(result)
            elif isinstance(result, Exception):
                logger.debug("Scan error: %s", result)

        logger.info("Discovery complete. Found %d devices.", len(devices))
        return devices

    async def discover_single_network(self, network: str) -> list[DeviceInfo]:
        """Discover devices on a single network."""
        return await self.discover_devices([network])
