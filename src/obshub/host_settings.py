class HostSettings:
    def __init__(self, host: str, port: int):
        """Host settings is a read-only class

        Args:
            host (str): hub host
            port (int): hub port
        """
        self.__host = host
        self.__port = port

    @property
    def host(self) -> str:
        return self.__host

    @host.setter
    def host(self, host: str) -> None:
        raise AttributeError("setting attribute 'host' is not allowed")

    @property
    def port(self) -> int:
        return self.__port

    @port.setter
    def port(self, port: int) -> None:
        raise AttributeError("setting attribute 'port' is not allowed")
