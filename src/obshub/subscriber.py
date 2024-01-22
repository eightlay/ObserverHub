from typing import Iterable

from obshub.event import Event
from obshub.client import Client


class Subscriber(Client):
    async def subscribe(self, topics: Iterable[str]) -> None:
        await self.send(Event.SUBSCRIBER.SUBSCRIBE, {"topics": topics})

    async def unsubscribe(self, topics: Iterable[str]) -> None:
        await self.send(Event.SUBSCRIBER.UNSUBSCRIBE, {"topics": topics})
