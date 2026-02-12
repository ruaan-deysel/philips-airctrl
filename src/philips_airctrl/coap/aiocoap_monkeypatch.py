"""Monkey patches for aiocoap library to improve reliability."""

import asyncio
import functools

from aiocoap.error import LibraryShutdown, NotObservable, ObservationCancelled
from aiocoap.messagemanager import MessageManager
from aiocoap.numbers.constants import EXCHANGE_LIFETIME
from aiocoap.protocol import ClientObservation


def _deduplicate_message(self, message):  # type: ignore[no-untyped-def]  # pragma: no cover
    key = (message.remote, message.mid)
    self.log.debug("MP: New unique message received")
    self.loop.call_later(EXCHANGE_LIFETIME, functools.partial(self._recent_messages.pop, key))
    self._recent_messages[key] = None
    return False


MessageManager._deduplicate_message = _deduplicate_message  # type: ignore[assignment]


def _iterator_del(self):  # type: ignore[no-untyped-def]  # pragma: no cover
    if self._future.done():
        try:
            self._future.result()
        except (ObservationCancelled, NotObservable):
            pass
        except LibraryShutdown:
            pass
        except asyncio.CancelledError:
            pass


ClientObservation._Iterator.__del__ = _iterator_del  # type: ignore[attr-defined]
