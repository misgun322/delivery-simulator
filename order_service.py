from delivery import DeliveryMethod
from models import Courier, Customer, Order, OrderItem, OrderStatus


class OrderService:
    def __init__(self, couriers: tuple[Courier, ...]) -> None:
        self._orders: dict[int, Order] = {}
        self._couriers = {courier.number: courier for courier in couriers}

    def create_order(
        self, customer: Customer, address: str, items: list[OrderItem]
    ) -> Order:
        if not items:
            raise ValueError("В заказе должна быть хотя бы одна позиция.")
        number = len(self._orders) + 1
        order = Order(number, customer, address)
        for item in items:
            order.add_item(item)
        self._orders[number] = order
        return order

    def get_order(self, number: int) -> Order:
        if number not in self._orders:
            raise ValueError(f"Заказ №{number} не найден.")
        return self._orders[number]

    def list_orders(self) -> tuple[Order, ...]:
        return tuple(self._orders.values())

    def list_couriers(self) -> tuple[Courier, ...]:
        return tuple(self._couriers.values())

    def set_delivery_method(self, number: int, method: DeliveryMethod) -> Order:
        order = self.get_order(number)
        order.set_delivery_method(method)
        return order

    def assign_courier(self, number: int, courier_number: int) -> Order:
        order = self.get_order(number)
        if courier_number not in self._couriers:
            raise ValueError(f"Курьер №{courier_number} не найден.")
        order.assign_courier(self._couriers[courier_number])
        return order

    def change_status(self, number: int, target: OrderStatus) -> Order:
        order = self.get_order(number)
        order.change_status(target)
        return order
