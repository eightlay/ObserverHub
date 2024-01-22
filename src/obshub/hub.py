import json
import logging
import asyncio
import websockets as ws
from collections import defaultdict
from typing import Any, Awaitable, Callable, Iterable

from obshub.event import Event
from obshub.topic import Topic
from obshub.client_type import ClientType
from obshub.host_settings import HostSettings
from obshub.join_key import JoinKey, generate_join_key
from obshub.exceptions import (
    HubCreationError,
    UnhandledEventError,
    WrongPublishDataError,
    JoinEventExpectedError,
)


class Hub:
    def __init__(
        self,
        host_settings: HostSettings,
        topics: Iterable[str] | None = None,
        only_predefined_topics: bool = False,
        allow_request_topics: bool = False,
        logger_name: str | None = None,
    ):
        """Hub for handling websocket connections and publishing updates to clients.

        Args:
            topics (Iterable[str], optional): if provided, only these topics
            will be allowed (i.e. `only_predefined_topics` must be set to
            True). Defaults to None.
            only_predefined_topics (bool, optional): if True, only topics
            provided in `topics` will be allowed. Defaults to False.
            allow_request_topics (bool, optional): if True, clients will be
            allowed to request current valid topics. Defaults to False.
            logger_name (str, optional): logger name. Defaults to `hub`
        """
        self.__check_creation_args(topics, only_predefined_topics)

        self.__only_predefined_topics = only_predefined_topics
        self.__allow_request_topics = allow_request_topics

        self._topics = set(Topic(t) for t in topics or [])

        self.__host_settings = host_settings

        self._publishers: dict[JoinKey, ws.WebSocketServerProtocol] = {}
        self._subscribers: dict[JoinKey, ws.WebSocketServerProtocol] = {}
        self._subscriptions: dict[Topic, set[JoinKey]] = defaultdict(set)

        self.__lock = asyncio.Lock()
        self.__logger = logging.getLogger(logger_name or "hub")

    def __check_creation_args(
        self, topics: Iterable[str] | None, only_predefined_topics: bool
    ) -> None:
        if topics is None and only_predefined_topics:
            raise HubCreationError(
                "`topics` must be provided if `only_predefined_topics` is True"
            )

        if topics is not None and not only_predefined_topics:
            raise HubCreationError(
                "`topics` must be None if `only_predefined_topics` is False"
            )

    async def serve(self) -> None:
        async with ws.serve(
            self.__handler,
            self.__host_settings.host,
            self.__host_settings.port,
        ):
            await asyncio.Future()

    async def __handler(self, websocket: ws.WebSocketServerProtocol) -> None:
        try:
            join_key, client_type = await self._register(websocket)
        except Exception as e:
            return await self._send_error(websocket, e)

        if client_type == ClientType.PUBLISHER:
            handler = self.__handle_publisher_event
        else:
            handler = self.__handle_subscriber_event

        try:
            await self.__handler_loop(websocket, join_key, handler)
        except Exception as e:
            self.__logger.error(f"Failed to handle client {join_key}")
            return self.__logger.error(e)
        finally:
            await self._unregister(join_key)

    async def _register(
        self, websocket: ws.WebSocketServerProtocol
    ) -> tuple[JoinKey, ClientType]:
        event = json.loads(await websocket.recv())

        if event["event"] != Event.GENERAL.JOIN.value:
            raise JoinEventExpectedError

        join_key = generate_join_key()

        async with self.__lock:
            # TODO: check if publisher has a right to join
            if "publisher_key" in event["data"]:
                client_type = ClientType.PUBLISHER
                self._publishers[join_key] = websocket
            else:
                client_type = ClientType.SUBSCRIBER
                self._subscribers[join_key] = websocket

        await self._send(
            join_key, websocket, Event.GENERAL.JOIN_ACCEPTED, {"join_key": join_key}
        )
        self.__logger.info(f"{client_type} {join_key} joined")

        return join_key, client_type

    async def _send_error(
        self, websocket: ws.WebSocketServerProtocol, error: Exception
    ) -> None:
        update = json.dumps({"event": Event.GENERAL.ERROR.value, "data": str(error)})
        await websocket.send(update)

    async def __handler_loop(
        self,
        websocket: ws.WebSocketServerProtocol,
        join_key: JoinKey,
        handler: Callable[
            [ws.WebSocketServerProtocol, JoinKey, dict[str, Any]], Awaitable[bool]
        ],
    ) -> None:
        async for message in websocket:
            event = json.loads(message)
            break_flag = await handler(websocket, join_key, event)

            if break_flag:
                break

    async def __handle_subscriber_event(
        self,
        websocket: ws.WebSocketServerProtocol,
        join_key: str,
        event: dict[str, Any],
    ) -> bool:
        match event["event"]:
            case Event.SUBSCRIBER.SUBSCRIBE.value | Event.SUBSCRIBER.UNSUBSCRIBE.value:
                await self.__handle_sub_unsub_event(websocket, join_key, event)
            case Event.GENERAL.LEAVE.value:
                await self._unregister(join_key)
                await self._send(join_key, websocket, Event.GENERAL.LEAVE_SUCCESS)
            case _:
                err = UnhandledEventError(event["event"])
                await self._send_error(websocket, err)
                return True

        return False

    async def __handle_sub_unsub_event(
        self,
        websocket: ws.WebSocketServerProtocol,
        join_key: str,
        event: dict[str, Any],
    ) -> bool:
        if "topics" not in event["data"]:
            # TODO: send error
            return True

        if not isinstance(event["data"]["topics"], Iterable):
            # TODO: send error
            return True

        topics = set(Topic(t) for t in event["data"]["topics"])

        if Event.SUBSCRIBER.SUBSCRIBE.value == event["event"]:
            invalid_topics = await self._subscribe_to_topics(join_key, topics)
            event_inval = Event.SUBSCRIBER.SUBSCRIBE_INVALID
            event_succ = Event.SUBSCRIBER.SUBSCRIBE_SUCCESS
        else:
            invalid_topics = await self._unsubscribe_from_topics(join_key, topics)
            event_inval = Event.SUBSCRIBER.UNSUBSCRIBE_INVALID
            event_succ = Event.SUBSCRIBER.UNSUBSCRIBE_SUCCESS

        if invalid_topics:
            await self._send(
                join_key,
                websocket,
                event_inval,
                {"invalid_topics": list(invalid_topics)},
            )
        else:
            await self._send(join_key, websocket, event_succ)

        return False

    async def _subscribe_to_topics(
        self, join_key: JoinKey, topics: set[Topic]
    ) -> set[Topic]:
        filtered_topics = set(topics) & self._topics

        async with self.__lock:
            for topic in filtered_topics:
                self._subscriptions[topic].add(join_key)

        self.__logger.info(f"Client {join_key} subscribed to topics {filtered_topics}")

        return set(topics) - filtered_topics

    async def _unsubscribe_from_topics(
        self,
        join_key: str,
        topics: Iterable[str],
    ) -> set[str]:
        invalid_topics: set[str] = set()

        async with self.__lock:
            for topic in topics:
                if join_key not in self._topics:
                    invalid_topics.add(topic)
                else:
                    self._subscriptions[topic].discard(join_key)

        self.__logger.info(f"Client {join_key} unsubscribed from topics")

        return invalid_topics

    async def __handle_publisher_event(
        self,
        websocket: ws.WebSocketServerProtocol,
        join_key: str,
        event: dict[str, Any],
    ) -> bool:
        match event["event"]:
            case Event.PUBLISHER.CREATE_TOPICS.value:
                await self.__handle_create_topics(websocket, event)
            case Event.PUBLISHER.DELETE_TOPICS.value:
                await self.__handle_delete_topics(websocket, event)
            case Event.PUBLISHER.REQUEST_TOPICS.value:
                await self.__handle_request_topics(websocket, event)
            case Event.PUBLISHER.PUBLISH.value:
                await self.__handle_publish(websocket, event)
            case Event.GENERAL.LEAVE.value:
                await self._unregister(join_key)
                await self._send(join_key, websocket, Event.GENERAL.LEAVE_SUCCESS)
            case _:
                err = UnhandledEventError(event["event"])
                await self._send_error(websocket, err)
                return True

        return False

    async def __handle_create_topics(
        self, websocket: ws.WebSocketServerProtocol, event: dict[str, Any]
    ) -> None:
        # TODO
        raise NotImplementedError

    async def __handle_delete_topics(
        self, websocket: ws.WebSocketServerProtocol, event: dict[str, Any]
    ) -> None:
        # TODO
        raise NotImplementedError

    async def __handle_request_topics(
        self, websocket: ws.WebSocketServerProtocol, event: dict[str, Any]
    ) -> None:
        # TODO
        raise NotImplementedError

    async def __handle_publish(
        self, websocket: ws.WebSocketServerProtocol, event: dict[str, Any]
    ) -> None:
        if "topic" not in event["data"]:
            return await self._send_error(
                websocket,
                WrongPublishDataError("publish event must have 'data.topic' field"),
            )

        if "update" not in event["data"]:
            return await self._send_error(
                websocket,
                WrongPublishDataError("publish event must have 'data.update' field"),
            )

        topic = Topic(event["data"]["topic"])

        async with self.__lock:
            if topic not in self._topics:
                if self.__only_predefined_topics:
                    err = f"you must create topic `{topic}` first"
                else:
                    err = "to create topic send `CREATE_TOPIC` event"

                return await self._send_error(websocket, WrongPublishDataError(err))

        update = json.dumps(
            {
                "event": Event.SUBSCRIBER.UPDATE,
                "data": {
                    "topic": topic,
                    "update": event["data"]["update"],
                },
            }
        )

        async with self.__lock:
            for join_key in self._subscriptions[topic]:
                await self.__send_string(join_key, self._subscribers[join_key], update)

    async def _send(
        self,
        join_key: JoinKey,
        websocket: ws.WebSocketServerProtocol,
        event: Event.GENERAL | Event.PUBLISHER | Event.SUBSCRIBER,
        data: Any = None,
    ) -> None:
        message = {"event": event.value}

        if data is not None:
            message["data"] = data

        await self.__send_string(join_key, websocket, json.dumps(message))

    async def __send_string(
        self,
        join_key: JoinKey,
        websocket: ws.WebSocketServerProtocol,
        message: str,
    ) -> None:
        try:
            await websocket.send(message)
        except ws.ConnectionClosed:
            await self._unregister(join_key)
        except Exception as e:
            self.__logger.error(f"Failed to send message to {join_key}")
            self.__logger.error(e)

    async def _unregister(self, join_key: JoinKey) -> None:
        async with self.__lock:
            if join_key in self._subscribers:
                del self._subscribers[join_key]

                for topic in self._topics:
                    self._subscriptions[topic].discard(join_key)

            self.__logger.info(f"Subscriber {join_key} left")

        async with self.__lock:
            if join_key in self._publishers:
                del self._publishers[join_key]

            self.__logger.info(f"Publisher {join_key} left")
