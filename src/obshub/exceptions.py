class HubCreationError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)


class JoinEventExpectedError(Exception):
    def __init__(self) -> None:
        super().__init__("invalid event: 'JOIN' expected")


class FailedToJoinServerError(Exception):
    def __init__(self, wrong_evet: str) -> None:
        super().__init__(f"failed to join server {wrong_evet}")


class UnhandledEventError(Exception):
    def __init__(self, event: str) -> None:
        super().__init__(f"unhandled event: {event}")


class ConnectionClosedUnexpectedlyError(Exception):
    def __init__(self) -> None:
        super().__init__("connection closed unexpectedly")


class WrongPublishDataError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(f"wrong publish data: {reason}")
