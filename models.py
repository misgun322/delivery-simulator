from dataclasses import dataclass
from decimal import Decimal

from delivery import DeliveryMethod


@dataclass(frozen=True)
class Customer:
    name: str
    phone: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.phone.strip():
            raise ValueError("Укажите имя и телефон клиента.")

    def __str__(self) -> str:
        return f"{self.name} ({self.phone})"


@dataclass(frozen=True)
class Courier:
    number: int
    name: str

    def __post_init__(self) -> None:
        if self.number < 1 or not self.name.strip():
            raise ValueError("Укажите положительный номер и имя курьера.")

    def __str__(self) -> str:
        return f"№{self.number} {self.name}"


@dataclass(frozen=True)
class OrderItem:
    name: str
    quantity: int
    unit_price: Decimal

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Укажите название товара.")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise ValueError("Количество должно быть целым числом больше нуля.")
        if not self.unit_price.is_finite() or self.unit_price < 0:
            raise ValueError("Цена должна быть конечным неотрицательным числом.")

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


class Order:
    def __init__(self, number: int, customer: Customer, address: str) -> None:
        self._number = number
        self._customer = customer
        self._address = address.strip()
        self._items: list[OrderItem] = []
        self._delivery_method: DeliveryMethod | None = None

    @property
    def number(self) -> int:
        return self._number

    @property
    def customer(self) -> Customer:
        return self._customer

    @property
    def address(self) -> str:
        return self._address

    @property
    def items(self) -> tuple[OrderItem, ...]:
        return tuple(self._items)

    @property
    def items_total(self) -> Decimal:
        return sum((item.subtotal for item in self._items), Decimal("0.00"))

    @property
    def delivery_method(self) -> DeliveryMethod | None:
        return self._delivery_method

    @property
    def delivery_cost(self) -> Decimal | None:
        if self._delivery_method is None:
            return None
        return self._delivery_method.calculate_cost(self)

    @property
    def delivery_hours(self) -> int | None:
        if self._delivery_method is None:
            return None
        return self._delivery_method.estimate_hours()

    @property
    def total_cost(self) -> Decimal:
        delivery_cost = self.delivery_cost
        return self.items_total if delivery_cost is None else self.items_total + delivery_cost

    def add_item(self, item: OrderItem) -> None:
        if not isinstance(item, OrderItem):
            raise ValueError("В заказ можно добавить только позицию заказа.")
        self._items.append(item)

    def set_delivery_method(self, method: DeliveryMethod) -> None:
        if method.requires_courier and not self._address:
            raise ValueError("Для курьерской доставки нужен адрес.")
        self._delivery_method = method
