from __future__ import annotations

from abc import abstractmethod


class _WritableFlushable:
    __slots__ = ()

    @abstractmethod
    def flush(self) -> None:
        pass

    @abstractmethod
    def write(self, s: str) -> int:
        pass


class Tee:
    """
    File-like object writing to two streams.
    """
    def __init__(self, stream1: _WritableFlushable, stream2: _WritableFlushable) -> None:
        self.stream1 = stream1
        self.stream2 = stream2

    def write(self, text: str) -> None:
        self.stream1.write(text)
        self.stream2.write(text)

    def flush(self) -> None:
        if hasattr(self.stream1, 'flush'):
            self.stream1.flush()
        if hasattr(self.stream2, 'flush'):
            self.stream2.flush()
