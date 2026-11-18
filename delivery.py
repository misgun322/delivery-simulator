from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import Order


class DeliveryMethod(ABC):
    name: str
    requires_courier: bool

    @abstractmethod
    def calculate_cost(self, order: "Order") -> Decimal:
        raise NotImplementedError

    @abstractmethod
    def estimate_hours(self) -> int:
        raise NotImplementedError


class StandardDelivery(DeliveryMethod):
    name = "Стандартная доставка"
    requires_courier = True

    def calculate_cost(self, order: "Order") -> Decimal:
        if order.items_total >= Decimal("3000.00"):
            return Decimal("0.00")
        return Decimal("300.00")

    def estimate_hours(self) -> int:
        return 48


class ExpressDelivery(DeliveryMethod):
    name = "Экспресс-доставка"
    requires_courier = True

    def calculate_cost(self, order: "Order") -> Decimal:
        quantity = sum(item.quantity for item in order.items)
        return Decimal("500.00") + Decimal("30.00") * max(0, quantity - 1)

    def estimate_hours(self) -> int:
        return 12


class PickupDelivery(DeliveryMethod):
    name = "Самовывоз"
    requires_courier = False

    def calculate_cost(self, order: "Order") -> Decimal:
        return Decimal("0.00")

    def estimate_hours(self) -> int:
        return 2
