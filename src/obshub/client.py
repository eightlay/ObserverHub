import json
import asyncio
import logging
from typing import Any
import websockets as ws

from obshub.event import Event
from obshub.exceptions import FailedToJoinServerError, ConnectionClosedUnexpectedlyError


class Client:
    def __init__(self, host: str, port: int, logger_name: str | None = None) -> None:
        """Publisher can create, delete topics and publish data to topics

        Args:
            host (str): `Hub` host
            port (int): `Hub` port
            logger_name (str | None, optional): logger name. Defaults to `publisher`
        """
        self._host: str = host
        self._port: int = port

        self._init: bool = False
        self._websocket: ws.WebSocketClientProtocol
        self.__logger = logging.getLogger(logger_name or "publisher")
        self.__lock = asyncio.Lock()

    async def send(
        self,
        event: Event.GENERAL | Event.PUBLISHER | Event.SUBSCRIBER,
        data: Any = None,
    ) -> None:
        update = {"event": event}

        if data is not None:
            update["data"] = data

        try:
            await self._websocket.send(json.dumps(update))
        except ws.ConnectionClosed:
            raise ConnectionClosedUnexpectedlyError

    async def recv(self):
        return self._websocket.recv()

    async def __aiter__(self):
        return self._websocket.__aiter__()

    async def connect(self):
        async with self.__lock:
            try:
                await self._get_connection()
            except OSError:
                self.__logger.error("Server is not running")
                return False

            try:
                join_key = await self._join_server()
                self.__logger.info(f"Successfully connected to server as {join_key}")
            except Exception as e:
                self.__logger.error("Failed to join server")
                self.__logger.error(e)
                return False

            self._init = True

        return True

    async def _get_connection(self) -> None:
        tries = 0
        websocket = None

        while tries < 5:
            try:
                websocket = await ws.connect(f"ws://{self._host}:{self._port}")
                break
            except OSError:
                tries += 1
                await asyncio.sleep(1)

        if not websocket:
            raise OSError

        self._websocket = websocket

    async def _join_server(self) -> None:
        await self.send(Event.GENERAL.JOIN)
        event = json.loads(await self._websocket.recv())

        if event["event"] != Event.GENERAL.JOIN_ACCEPTED.value:
            raise FailedToJoinServerError(event["event"])

        return event["data"]["join_key"]

    async def disconnect(self) -> None:
        async with self.__lock:
            self._init = False
            await self.send(Event.GENERAL.LEAVE)
            await self._websocket.close()
