"""Tests for the CoAP client module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiocoap.error import NetworkError

from philips_airctrl.coap.client import Client


class TestClient:
    def test_init(self):
        client = Client("192.168.1.100", 5683)
        assert client.host == "192.168.1.100"
        assert client.port == 5683
        assert client._client_context is None
        assert client._encryption_context is None

    def test_init_default_port(self):
        client = Client("192.168.1.100")
        assert client.port == 5683

    def test_class_attributes(self):
        assert Client.STATUS_PATH == "/sys/dev/status"
        assert Client.CONTROL_PATH == "/sys/dev/control"
        assert Client.SYNC_PATH == "/sys/dev/sync"

    @pytest.mark.asyncio
    async def test_create_factory_method(self):
        with patch.object(Client, "_init", new_callable=AsyncMock) as mock_init:
            client = await Client.create("192.168.1.100", 5684)
            assert isinstance(client, Client)
            assert client.host == "192.168.1.100"
            assert client.port == 5684
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        with patch.object(Client, "_init", new_callable=AsyncMock) as mock_init:
            async with Client("192.168.1.100") as client:
                assert isinstance(client, Client)
                mock_init.assert_called_once()
                # Set up a mock context so shutdown works
                client._client_context = AsyncMock()

            client._client_context.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager_no_context(self):
        with patch.object(Client, "_init", new_callable=AsyncMock):
            async with Client("192.168.1.100"):
                pass  # shutdown with no _client_context should not raise

    @pytest.mark.asyncio
    async def test_shutdown(self):
        client = Client("192.168.1.100")
        mock_context = AsyncMock()
        client._client_context = mock_context

        await client.shutdown()
        mock_context.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_no_context(self):
        client = Client("192.168.1.100")
        await client.shutdown()

    @pytest.mark.asyncio
    async def test_sync(self):
        client = Client("192.168.1.100")

        mock_context = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.decode.return_value = "ABCD1234"

        mock_requester = MagicMock()

        async def mock_response_coro():
            return mock_response

        mock_requester.response = mock_response_coro()
        mock_context.request.return_value = mock_requester

        mock_encryption = MagicMock()

        client._client_context = mock_context
        client._encryption_context = mock_encryption

        with patch("os.urandom") as mock_urandom:
            mock_urandom.return_value = b"\x12\x34\x56\x78"
            await client._sync()

            mock_context.request.assert_called_once()
            call_args = mock_context.request.call_args[0][0]
            assert call_args.payload == b"12345678"
            mock_encryption.set_client_key.assert_called_once_with("ABCD1234")

    @pytest.mark.asyncio
    async def test_get_status(self):
        client = Client("192.168.1.100")

        mock_context = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.decode.return_value = "encrypted_payload"
        mock_response.opt.max_age = 120

        mock_requester = MagicMock()

        async def mock_response_coro():
            return mock_response

        mock_requester.response = mock_response_coro()
        mock_context.request.return_value = mock_requester

        mock_encryption = MagicMock()
        decrypted_payload = '{"state": {"reported": {"power": true, "mode": "auto"}}}'
        mock_encryption.decrypt.return_value = decrypted_payload

        client._client_context = mock_context
        client._encryption_context = mock_encryption

        status, max_age = await client.get_status()

        mock_context.request.assert_called_once()
        call_args = mock_context.request.call_args[0][0]
        assert call_args.opt.observe == 0
        mock_encryption.decrypt.assert_called_once_with("encrypted_payload")
        assert status == {"power": True, "mode": "auto"}
        assert max_age == 120

    @pytest.mark.asyncio
    async def test_get_status_no_max_age(self):
        client = Client("192.168.1.100")

        mock_context = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.decode.return_value = "encrypted_payload"
        mock_opt = MagicMock()
        del mock_opt.max_age
        mock_response.opt = mock_opt

        mock_requester = MagicMock()

        async def mock_response_coro():
            return mock_response

        mock_requester.response = mock_response_coro()
        mock_context.request.return_value = mock_requester

        mock_encryption = MagicMock()
        decrypted_payload = '{"state": {"reported": {"power": true}}}'
        mock_encryption.decrypt.return_value = decrypted_payload

        client._client_context = mock_context
        client._encryption_context = mock_encryption

        status, max_age = await client.get_status()

        assert status == {"power": True}
        assert max_age == 60

    @pytest.mark.asyncio
    async def test_get_status_network_error(self):
        client = Client("192.168.1.100")

        mock_context = MagicMock()
        mock_requester = MagicMock()

        async def mock_response_coro():
            raise NetworkError("connection failed")

        mock_requester.response = mock_response_coro()
        mock_context.request.return_value = mock_requester

        client._client_context = mock_context
        client._encryption_context = MagicMock()

        with pytest.raises(NetworkError):
            await client.get_status()

    @pytest.mark.asyncio
    async def test_set_control_value(self):
        client = Client("192.168.1.100")

        with patch.object(client, "set_control_values", new_callable=AsyncMock) as mock_set:
            mock_set.return_value = True

            result = await client.set_control_value("power", True)

            mock_set.assert_called_once_with(
                data={"power": True},
                retry_count=5,
                resync=True,
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_set_control_values_success(self):
        client = Client("192.168.1.100")

        mock_context = MagicMock()
        mock_response = MagicMock()
        mock_response.payload = b'{"status": "success"}'

        mock_requester = MagicMock()

        async def mock_response_coro():
            return mock_response

        mock_requester.response = mock_response_coro()
        mock_context.request.return_value = mock_requester

        mock_encryption = MagicMock()
        mock_encryption.encrypt.return_value = "encrypted_payload"

        client._client_context = mock_context
        client._encryption_context = mock_encryption

        data = {"power": True, "mode": "auto"}
        result = await client.set_control_values(data)

        mock_context.request.assert_called_once()
        call_args = mock_context.request.call_args[0][0]
        assert call_args.payload == b"encrypted_payload"

        mock_encryption.encrypt.assert_called_once()
        encrypted_call_args = mock_encryption.encrypt.call_args[0][0]
        payload_data = json.loads(encrypted_call_args)
        assert payload_data == {
            "state": {
                "desired": {
                    "CommandType": "app",
                    "DeviceId": "",
                    "EnduserId": "",
                    "power": True,
                    "mode": "auto",
                }
            }
        }
        assert result is True

    @pytest.mark.asyncio
    async def test_set_control_values_failure_no_retry(self):
        client = Client("192.168.1.100")

        mock_context = MagicMock()
        mock_encryption = MagicMock()
        mock_encryption.encrypt.return_value = "encrypted"

        mock_response = MagicMock()
        mock_response.payload = b'{"status": "failed"}'
        mock_requester = MagicMock()

        async def coro():
            return mock_response

        mock_requester.response = coro()
        mock_context.request.return_value = mock_requester

        client._client_context = mock_context
        client._encryption_context = mock_encryption

        result = await client.set_control_values({"power": True}, retry_count=0, resync=False)
        assert result is False

    @pytest.mark.asyncio
    async def test_set_control_values_failure_with_resync(self):
        client = Client("192.168.1.100")

        mock_context = MagicMock()
        mock_encryption = MagicMock()
        mock_encryption.encrypt.return_value = "encrypted"

        # First call fails, second succeeds
        responses = [b'{"status": "failed"}', b'{"status": "success"}']
        response_idx = 0

        def make_requester():
            nonlocal response_idx
            mock_response = MagicMock()
            mock_response.payload = responses[min(response_idx, len(responses) - 1)]
            response_idx += 1
            mock_requester = MagicMock()

            async def coro():
                return mock_response

            mock_requester.response = coro()
            return mock_requester

        mock_context.request.side_effect = lambda _: make_requester()

        client._client_context = mock_context
        client._encryption_context = mock_encryption

        sync_called = False

        async def mock_sync():
            nonlocal sync_called
            sync_called = True

        client._sync = mock_sync

        with patch("philips_airctrl.coap.client.asyncio.sleep", new_callable=AsyncMock) as mock_sl:
            result = await client.set_control_values({"power": True}, retry_count=1, resync=True)

        assert result is True
        assert sync_called is True
        mock_sl.assert_called_once_with(0.5)

    @pytest.mark.asyncio
    async def test_set_control_values_iterative_retry_exhaustion(self):
        """Test that iterative retry exhausts all attempts with sleep between them."""
        client = Client("192.168.1.100")

        mock_context = MagicMock()
        mock_encryption = MagicMock()
        mock_encryption.encrypt.return_value = "encrypted"

        request_count = 0

        def make_requester():
            nonlocal request_count
            request_count += 1
            mock_response = MagicMock()
            mock_response.payload = b'{"status": "failed"}'
            mock_requester = MagicMock()

            async def coro():
                return mock_response

            mock_requester.response = coro()
            return mock_requester

        mock_context.request.side_effect = lambda _: make_requester()

        client._client_context = mock_context
        client._encryption_context = mock_encryption

        async def mock_sync():
            pass

        client._sync = mock_sync

        with patch("philips_airctrl.coap.client.asyncio.sleep", new_callable=AsyncMock) as mock_sl:
            result = await client.set_control_values({"power": True}, retry_count=3, resync=False)

        assert result is False
        # Initial attempt + 3 retries = 4 total requests
        assert request_count == 4
        # Sleep called between retries (3 times, not after final attempt)
        assert mock_sl.call_count == 3

    @pytest.mark.asyncio
    async def test_observe_status(self):
        client = Client("192.168.1.100")

        mock_context = MagicMock()
        mock_encryption = MagicMock()

        initial_response = MagicMock()
        initial_response.payload.decode.return_value = "enc1"

        obs_response = MagicMock()
        obs_response.payload.decode.return_value = "enc2"

        mock_encryption.decrypt.side_effect = [
            '{"state": {"reported": {"power": true}}}',
            '{"state": {"reported": {"power": false}}}',
        ]

        mock_requester = MagicMock()

        async def mock_response_coro():
            return initial_response

        mock_requester.response = mock_response_coro()

        async def mock_observation():
            yield obs_response

        mock_requester.observation = mock_observation()
        mock_context.request.return_value = mock_requester

        client._client_context = mock_context
        client._encryption_context = mock_encryption

        results = []
        async for status in client.observe_status():
            results.append(status)

        assert len(results) == 2
        assert results[0] == {"power": True}
        assert results[1] == {"power": False}

    @pytest.mark.asyncio
    async def test_init_method(self):
        with (
            patch("philips_airctrl.coap.client.Context") as mock_ctx_class,
            patch.object(Client, "_sync", new_callable=AsyncMock) as mock_sync,
        ):
            mock_ctx_class.create_client_context = AsyncMock(return_value=MagicMock())
            client = Client("192.168.1.100")
            await client._init()

            mock_ctx_class.create_client_context.assert_called_once()
            assert client._encryption_context is not None
            mock_sync.assert_called_once()
