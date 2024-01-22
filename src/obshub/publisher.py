from typing import Any, Iterable

from obshub.event import Event
from obshub.client import Client


class Publisher(Client):
    async def create_topics(self, topics: Iterable[str]) -> None:
        await self.send(Event.PUBLISHER.CREATE_TOPICS, {"topics": topics})

    async def delete_topics(self, topics: Iterable[str]) -> None:
        await self.send(Event.PUBLISHER.DELETE_TOPICS, {"topics": topics})

    async def publish(self, topic: str, data: Any) -> None:
        await self.send(Event.PUBLISHER.PUBLISH, {"topic": topic, "data": data})
