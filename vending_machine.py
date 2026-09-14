import threading
from abc import ABC, abstractmethod


class Item:
    def __init__(self, name: str, price: int):
        self.name = name
        self.price = price


class State(ABC):
    @abstractmethod
    def insert_money(self, machine: "VendingMachine", amount: int) -> None:
        pass

    @abstractmethod
    def select_item(self, machine: "VendingMachine", code: str) -> None:
        pass

    @abstractmethod
    def dispense(self, machine: "VendingMachine") -> tuple[Item, int]:
        pass

    @abstractmethod
    def refund(self, machine: "VendingMachine") -> int:
        pass


class IdleState(State):
    def insert_money(self, machine: "VendingMachine", amount: int) -> None:
        machine.balance += amount
        machine.set_state(HasMoneyState())

    def select_item(self, machine: "VendingMachine", code: str) -> None:
        raise ValueError("Insert money first")

    def dispense(self, machine: "VendingMachine") -> tuple[Item, int]:
        raise ValueError("Insert money and select an item first")

    def refund(self, machine: "VendingMachine") -> int:
        raise ValueError("No money to refund")


class HasMoneyState(State):
    def insert_money(self, machine: "VendingMachine", amount: int) -> None:
        machine.balance += amount

    def select_item(self, machine: "VendingMachine", code: str) -> None:
        item = machine.inventory.get_item(code)

        if item is None:
            raise ValueError("Invalid item")

        if machine.inventory.get_quantity(code) <= 0:
            raise ValueError("Item is out of stock")

        machine.selected_code = code
        machine.set_state(ItemSelectedState())

    def dispense(self, machine: "VendingMachine") -> tuple[Item, int]:
        raise ValueError("Select an item first")

    def refund(self, machine: "VendingMachine") -> int:
        amount = machine.balance

        machine.balance = 0
        machine.set_state(IdleState())

        return amount


class ItemSelectedState(State):
    def insert_money(self, machine: "VendingMachine", amount: int) -> None:
        machine.balance += amount

    def select_item(self, machine: "VendingMachine", code: str) -> None:
        raise ValueError("Item already selected")

    def dispense(self, machine: "VendingMachine") -> tuple[Item, int]:
        code = machine.selected_code

        if code is None:
            raise ValueError("No item selected")

        item = machine.inventory.get_item(code)

        if item is None:
            raise ValueError("Invalid item")

        if machine.balance < item.price:
            raise ValueError("Insufficient balance")

        machine.set_state(DispensingState())

        return machine.current_state.dispense(machine)

    def refund(self, machine: "VendingMachine") -> int:
        amount = machine.balance

        machine.balance = 0
        machine.selected_code = None
        machine.set_state(IdleState())

        return amount


class DispensingState(State):
    def insert_money(self, machine: "VendingMachine", amount: int) -> None:
        raise ValueError("Currently dispensing")

    def select_item(self, machine: "VendingMachine", code: str) -> None:
        raise ValueError("Currently dispensing")

    def dispense(self, machine: "VendingMachine") -> tuple[Item, int]:
        code = machine.selected_code

        if code is None:
            raise ValueError("No item selected")

        item = machine.inventory.get_item(code)

        if item is None:
            raise ValueError("Invalid item")

        machine.inventory.deduct_stock(code)

        change = machine.balance - item.price

        machine.balance = 0
        machine.selected_code = None
        machine.set_state(IdleState())

        return item, change

    def refund(self, machine: "VendingMachine") -> int:
        raise ValueError("Cannot refund while dispensing")


class Inventory:
    def __init__(self) -> None:
        self._items: dict[str, Item] = {}
        self._stock: dict[str, int] = {}

    def add_item(self, code: str, item: Item, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        self._items[code] = item
        self._stock[code] = self._stock.get(code, 0) + quantity

    def get_item(self, code: str) -> Item | None:
        return self._items.get(code)

    def get_quantity(self, code: str) -> int:
        return self._stock.get(code, 0)

    def deduct_stock(self, code: str) -> None:
        if self._stock.get(code, 0) <= 0:
            raise ValueError(f"Item '{code}' is out of stock")

        self._stock[code] -= 1


class VendingMachine:
    def __init__(self) -> None:
        self.inventory = Inventory()
        self.balance = 0
        self.selected_code: str | None = None
        self.current_state: State = IdleState()

        self.lock = threading.Lock()

    def set_state(self, state: State) -> None:
        self.current_state = state

    def insert_money(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Enter valid positive amount")

        with self.lock:
            self.current_state.insert_money(self, amount)

    def select_item(self, code: str) -> None:
        with self.lock:
            self.current_state.select_item(self, code)

    def dispense(self) -> tuple[Item, int]:
        with self.lock:
            return self.current_state.dispense(self)

    def refund(self) -> int:
        with self.lock:
            return self.current_state.refund(self)


if __name__ == "__main__":
    vm = VendingMachine()

    vm.inventory.add_item("A1", Item("Coke", 40), 5)
    vm.inventory.add_item("B1", Item("Pepsi", 35), 3)

    vm.insert_money(50)
    vm.select_item("A1")

    item, change = vm.dispense()

    print(f"Dispensed: {item.name}")
    print(f"Change: {change}")
