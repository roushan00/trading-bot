from abc import ABC, abstractmethod
from decimal import Decimal


class BaseBroker(ABC):
    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        price: Decimal,
        order_id: int,
    ) -> dict:
        ...

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> dict:
        ...

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> dict:
        ...

    @abstractmethod
    async def get_positions(self) -> list[dict]:
        ...

    @abstractmethod
    async def square_off_all(self) -> list[dict]:
        ...
