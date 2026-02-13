"""Tests for package-level imports."""

from unittest.mock import patch


def test_version():
    from philips_airctrl import __version__
    from philips_airctrl._version import __version__ as direct_version

    assert isinstance(__version__, str)
    assert __version__ == direct_version


def test_exports():
    from philips_airctrl import CoAPClient
    from philips_airctrl.coap.client import Client

    assert CoAPClient is Client


def test_coap_init_export():
    from philips_airctrl.coap import Client
    from philips_airctrl.coap.client import Client as DirectClient

    assert Client is DirectClient


def test_main_module():
    with patch("philips_airctrl.cli.main"):
        import philips_airctrl.__main__  # noqa: F401
