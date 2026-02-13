"""Client to interact with the aiocoap library."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from aiocoap import Context, Message, Unreliable
from aiocoap.error import NetworkError
from aiocoap.numbers.codes import GET, POST

from philips_airctrl.coap.encryption import EncryptionContext

logger = logging.getLogger(__name__)

RETRY_DELAY = 0.5


class Client:
    STATUS_PATH = "/sys/dev/status"
    CONTROL_PATH = "/sys/dev/control"
    SYNC_PATH = "/sys/dev/sync"

    def __init__(self, host: str, port: int = 5683) -> None:
        self.host = host
        self.port = port
        self._client_context: Context | None = None
        self._encryption_context: EncryptionContext | None = None

    async def _init(self) -> None:
        self._client_context = await Context.create_client_context()
        self._encryption_context = EncryptionContext()
        await self._sync()

    @classmethod
    async def create(cls, *args: Any, **kwargs: Any) -> Client:
        obj = cls(*args, **kwargs)
        await obj._init()
        return obj

    async def __aenter__(self) -> Client:
        await self._init()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.shutdown()

    async def shutdown(self) -> None:
        if self._client_context:
            await self._client_context.shutdown()

    async def _sync(self) -> None:
        logger.debug("syncing")
        sync_request = os.urandom(4).hex().upper()
        request = Message(
            code=POST,
            transport_tuning=Unreliable,
            uri=f"coap://{self.host}:{self.port}{self.SYNC_PATH}",
            payload=sync_request.encode(),
        )
        response = await self._client_context.request(request).response
        client_key = response.payload.decode()
        logger.debug("synced: %s", client_key)
        self._encryption_context.set_client_key(client_key)

    async def get_status(self) -> tuple[dict[str, Any], int]:
        logger.debug("retrieving status")
        request = Message(
            code=GET,
            transport_tuning=Unreliable,
            uri=f"coap://{self.host}:{self.port}{self.STATUS_PATH}",
        )
        request.opt.observe = 0
        try:
            response = await self._client_context.request(request).response
        except NetworkError:
            logger.error("network error while retrieving status")
            raise
        payload_encrypted = response.payload.decode()
        payload = self._encryption_context.decrypt(payload_encrypted)
        logger.debug("status: %s", payload)
        state_reported = json.loads(payload)
        max_age = 60
        try:
            max_age = response.opt.max_age
            logger.debug("max age = %s", max_age)
        except AttributeError:
            logger.debug("no max age found in CoAP options")
        return state_reported["state"]["reported"], max_age

    async def observe_status(self) -> AsyncIterator[dict[str, Any]]:
        def decrypt_status(response: Any) -> dict[str, Any]:
            payload_encrypted = response.payload.decode()
            payload = self._encryption_context.decrypt(payload_encrypted)
            logger.debug("observation status: %s", payload)
            status = json.loads(payload)
            return status["state"]["reported"]

        logger.debug("observing status")
        request = Message(
            code=GET,
            transport_tuning=Unreliable,
            uri=f"coap://{self.host}:{self.port}{self.STATUS_PATH}",
        )
        request.opt.observe = 0
        requester = self._client_context.request(request)
        response = await requester.response
        yield decrypt_status(response)
        async for response in requester.observation:
            yield decrypt_status(response)

    async def set_control_value(
        self, key: str, value: Any, retry_count: int = 5, resync: bool = True
    ) -> bool | None:
        return await self.set_control_values(
            data={key: value}, retry_count=retry_count, resync=resync
        )

    async def set_control_values(
        self, data: dict[str, Any], retry_count: int = 5, resync: bool = True
    ) -> bool | None:
        state_desired = {
            "state": {
                "desired": {
                    "CommandType": "app",
                    "DeviceId": "",
                    "EnduserId": "",
                    **data,
                }
            }
        }
        payload = json.dumps(state_desired)
        logger.debug("REQUEST: %s", payload)
        payload_encrypted = self._encryption_context.encrypt(payload)

        for attempt in range(retry_count + 1):
            request = Message(
                code=POST,
                transport_tuning=Unreliable,
                uri=f"coap://{self.host}:{self.port}{self.CONTROL_PATH}",
                payload=payload_encrypted.encode(),
            )
            response = await self._client_context.request(request).response
            logger.debug("RESPONSE: %s", response.payload)
            result = json.loads(response.payload)
            if result.get("status") == "success":
                return True
            if resync:
                logger.debug("set_control_value failed. resyncing...")
                await self._sync()
            if attempt < retry_count:
                logger.debug("set_control_value failed. retrying...")
                await asyncio.sleep(RETRY_DELAY)

        logger.error("set_control_value failed: %s", data)
        return False
