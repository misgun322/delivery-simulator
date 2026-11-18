import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from delivery import DeliveryMethod, ExpressDelivery, PickupDelivery, StandardDelivery
from models import Courier, Customer, Order, OrderItem, OrderStatus
from order_service import OrderService


class OrderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.customer = Customer("Анна", "+79000000000")
        self.order = Order(1, self.customer, "ул. Мира, 10")
        self.item = OrderItem("Книга", 2, Decimal("150.25"))
        self.order.add_item(self.item)

    def test_composition_and_item_total(self) -> None:
        self.assertIs(self.order.customer, self.customer)
        self.assertEqual(self.order.items, (self.item,))
        self.assertEqual(self.item.subtotal, Decimal("300.50"))
        self.assertEqual(self.order.total_cost, Decimal("300.50"))
        self.assertIsNone(self.order.delivery_cost)
        with self.assertRaises(FrozenInstanceError):
            self.item.quantity = 3
        with self.assertRaises(AttributeError):
            self.order.status = OrderStatus.DELIVERED

    def test_invalid_item_prices(self) -> None:
        for price in ("-0.01", "NaN", "Infinity"):
            with self.subTest(price=price), self.assertRaisesRegex(ValueError, "Цена"):
                OrderItem("Книга", 1, Decimal(price))

    def test_invalid_item_quantities(self) -> None:
        for quantity in (0, -1, 1.5, True):
            with self.subTest(quantity=quantity), self.assertRaisesRegex(
                ValueError, "Количество"
            ):
                OrderItem("Книга", quantity, Decimal("1"))

    def test_blank_names_and_customer_contact_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Customer("Анна", " ")
        with self.assertRaises(ValueError):
            Customer(" ", "123")
        with self.assertRaises(ValueError):
            Courier(1, " ")
        with self.assertRaises(ValueError):
            OrderItem(" ", 1, Decimal("1"))

    def test_delivery_contract_is_abstract(self) -> None:
        with self.assertRaises(TypeError):
            DeliveryMethod()

    def test_delivery_methods_via_order(self) -> None:
        for method, fee, hours in (
            (StandardDelivery(), "300.00", 48),
            (ExpressDelivery(), "530.00", 12),
            (PickupDelivery(), "0.00", 2),
        ):
            with self.subTest(method=method.name):
                self.order.set_delivery_method(method)
                self.assertIs(self.order.delivery_method, method)
                self.assertEqual(self.order.delivery_cost, Decimal(fee))
                self.assertEqual(self.order.delivery_hours, hours)
                self.assertEqual(self.order.total_cost, Decimal("300.50") + Decimal(fee))

    def test_standard_delivery_is_free_at_threshold(self) -> None:
        self.order.add_item(OrderItem("Подарок", 1, Decimal("2699.50")))
        self.order.set_delivery_method(StandardDelivery())
        self.assertEqual(self.order.items_total, Decimal("3000.00"))
        self.assertEqual(self.order.delivery_cost, Decimal("0.00"))

    def test_courier_delivery_requires_an_address(self) -> None:
        order = Order(1, self.customer, " ")
        for method in (StandardDelivery(), ExpressDelivery()):
            with self.subTest(method=method.name), self.assertRaisesRegex(ValueError, "адрес"):
                order.set_delivery_method(method)
        self.assertIsNone(order.delivery_method)
        order.set_delivery_method(PickupDelivery())
        self.assertEqual(order.address, "")

    def test_switching_to_pickup_clears_assigned_courier(self) -> None:
        self.order.set_delivery_method(StandardDelivery())
        self.order.assign_courier(Courier(1, "Алексей"))
        self.order.set_delivery_method(PickupDelivery())
        self.assertIsNone(self.order.courier)
        with self.assertRaisesRegex(ValueError, "курьер не нужен"):
            self.order.assign_courier(Courier(2, "Мария"))

    def test_methods_reject_invalid_argument_types(self) -> None:
        with self.assertRaisesRegex(ValueError, "способов доставки"):
            self.order.set_delivery_method("Самовывоз")
        self.order.set_delivery_method(StandardDelivery())
        with self.assertRaisesRegex(ValueError, "только курьера"):
            self.order.assign_courier(self.customer)
        with self.assertRaisesRegex(ValueError, "статусов"):
            self.order.change_status("Новый")
        self.assertIsNone(self.order.courier)
        self.assertIs(self.order.status, OrderStatus.NEW)


class OrderServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.courier = Courier(1, "Алексей")
        self.service = OrderService((self.courier,))
        self.customer = Customer("Анна", "123")
        self.items = [OrderItem("Книга", 1, Decimal("100.00"))]

    def test_create_list_and_find_orders(self) -> None:
        first = self.service.create_order(self.customer, "ул. Мира, 10", self.items)
        second = self.service.create_order(self.customer, "", self.items)
        self.assertEqual((first.number, second.number), (1, 2))
        self.assertEqual(self.service.list_orders(), (first, second))
        self.assertIs(self.service.get_order(2), second)
        self.assertEqual(self.service.list_couriers(), (self.courier,))
        self.assertEqual(OrderService(()).list_orders(), ())

    def test_empty_order_is_not_saved(self) -> None:
        with self.assertRaisesRegex(ValueError, "хотя бы одна позиция"):
            self.service.create_order(self.customer, "", [])
        self.assertEqual(self.service.list_orders(), ())

    def test_unknown_order_and_courier(self) -> None:
        with self.assertRaisesRegex(ValueError, "Заказ №50 не найден"):
            self.service.change_status(50, OrderStatus.CANCELLED)
        order = self.service.create_order(self.customer, "ул. Мира, 10", self.items)
        self.service.set_delivery_method(order.number, StandardDelivery())
        with self.assertRaisesRegex(ValueError, "Курьер №50 не найден"):
            self.service.assign_courier(order.number, 50)
        self.assertIsNone(order.courier)

    def test_confirmation_requires_delivery_method(self) -> None:
        order = self.service.create_order(self.customer, "ул. Мира, 10", self.items)
        with self.assertRaisesRegex(ValueError, "выберите способ доставки"):
            self.service.change_status(order.number, OrderStatus.CONFIRMED)
        self.assertIs(order.status, OrderStatus.NEW)

    def test_courier_order_requires_assignment_before_dispatch(self) -> None:
        order = self.service.create_order(self.customer, "ул. Мира, 10", self.items)
        self.service.set_delivery_method(order.number, ExpressDelivery())
        self.service.change_status(order.number, OrderStatus.CONFIRMED)
        with self.assertRaisesRegex(ValueError, "назначьте курьера"):
            self.service.change_status(order.number, OrderStatus.IN_DELIVERY)
        with self.assertRaisesRegex(ValueError, "только для самовывоза"):
            self.service.change_status(order.number, OrderStatus.READY_FOR_PICKUP)
        self.assertIs(order.status, OrderStatus.CONFIRMED)
        self.service.assign_courier(order.number, self.courier.number)
        self.service.change_status(order.number, OrderStatus.IN_DELIVERY)
        self.service.change_status(order.number, OrderStatus.DELIVERED)
        self.assertIs(order.courier, self.courier)
        self.assertIs(order.status, OrderStatus.DELIVERED)
        with self.assertRaisesRegex(ValueError, "Недопустимый переход"):
            self.service.change_status(order.number, OrderStatus.CANCELLED)

    def test_pickup_can_finish_without_courier(self) -> None:
        order = self.service.create_order(self.customer, "", self.items)
        self.service.set_delivery_method(order.number, PickupDelivery())
        self.service.change_status(order.number, OrderStatus.CONFIRMED)
        with self.assertRaisesRegex(ValueError, "курьер не нужен"):
            self.service.assign_courier(order.number, self.courier.number)
        with self.assertRaisesRegex(ValueError, "Готов к самовывозу"):
            self.service.change_status(order.number, OrderStatus.IN_DELIVERY)
        self.service.change_status(order.number, OrderStatus.READY_FOR_PICKUP)
        self.service.change_status(order.number, OrderStatus.DELIVERED)
        self.assertIsNone(order.courier)
        self.assertIs(order.status, OrderStatus.DELIVERED)

    def test_cancellation_is_final(self) -> None:
        order = self.service.create_order(self.customer, "", self.items)
        with self.assertRaisesRegex(ValueError, "Недопустимый переход"):
            self.service.change_status(order.number, OrderStatus.DELIVERED)
        self.service.change_status(order.number, OrderStatus.CANCELLED)
        with self.assertRaisesRegex(ValueError, "Недопустимый переход"):
            self.service.change_status(order.number, OrderStatus.CONFIRMED)
        self.assertIs(order.status, OrderStatus.CANCELLED)

    def test_order_items_and_delivery_are_locked_after_confirmation(self) -> None:
        order = self.service.create_order(self.customer, "", self.items)
        self.service.set_delivery_method(order.number, PickupDelivery())
        self.service.change_status(order.number, OrderStatus.CONFIRMED)
        with self.assertRaisesRegex(ValueError, "только в новый заказ"):
            order.add_item(self.items[0])
        with self.assertRaisesRegex(ValueError, "только для нового заказа"):
            self.service.set_delivery_method(order.number, StandardDelivery())
        self.assertEqual(order.items, tuple(self.items))
        self.assertIsInstance(order.delivery_method, PickupDelivery)
