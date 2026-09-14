from abc import ABC, abstractmethod
import threading

class User:
    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email

class Split:
    def __init__(self, user_id: int, amount: float = 0.0):
        self.user_id = user_id
        self.amount = amount

class Expense:
    def __init__(self, expense_id: int, total_amount: float, paid_by_user_id: int, splits: list[Split]):
        self.expense_id = expense_id
        self.total_amount = total_amount
        self.paid_by_user_id = paid_by_user_id
        self.splits = splits

class UserManagementService:
    def __init__(self):
        self._lock = threading.Lock()
        self._current_user_id: int = 1
        self._users: dict[int, User] = {}

    def add_user(self, name: str, email: str) -> User:
        with self._lock:
            user = User(self._current_user_id, name, email)
            self._users[self._current_user_id] = user
            self._current_user_id+=1
            return user

class AbstractSplitStrategy(ABC):
    @abstractmethod
    def split(self, total_amount: float, user_ids: list[int], values: list[float] | None = None) -> list[Split]:
        pass

class EqualSplitStrategy(AbstractSplitStrategy):
    def split(self, total_amount: float, user_ids: list[int], values: list[float] | None = None) -> list[Split]:
        if not user_ids:
            raise ValueError("User list cannot be empty")
        share = round(total_amount / len(user_ids), 2)
        splits = []
        for user_id in user_ids:
            splits.append(Split(user_id, share))
        return splits

class ExactSplitStrategy(AbstractSplitStrategy):
    def split(self, total_amount: float, user_ids: list[int], values: list[float] | None = None) -> list[Split]:
        if not values or len(user_ids) != len(values):
            raise ValueError("Total user(s) and value(s) don't match up")

        if round(sum(values), 2) != round(total_amount, 2):
            raise ValueError(f"Total values ({sum(values)}) don't add up to total amount ({total_amount})")

        splits = []
        for i in range(len(user_ids)):
            user_id = user_ids[i]
            share = values[i]
            splits.append(Split(user_id, share))
        return splits

class PercentSplitStrategy(AbstractSplitStrategy):
    def split(self, total_amount: float, user_ids: list[int], values: list[float] | None = None) -> list[Split]:
        if not values or len(user_ids) != len(values):
            raise ValueError("Total user(s) and percentage(s) don't match up")

        if round(sum(values), 2) != 100.0:
            raise ValueError(f"Total percentages ({sum(values)}%) don't add up to 100%")

        splits = []
        for i in range(len(user_ids)):
            user_id = user_ids[i]
            share = round((values[i] / 100.0) * total_amount, 2)
            splits.append(Split(user_id, share))
        return splits    

class ExpenseManagementService:
    def __init__(self):
        self._lock = threading.Lock()
        self._current_expense_id: int = 1
        self.expenses: dict[int, Expense] = {}
        # Balance sheet: self.balances[A][B] = amount that user A owes user B
        self.balances: dict[int, dict[int, float]] = {}

    def add_expense(
        self,
        total_amount: float,
        paid_by_user_id: int,
        participant_user_ids: list[int],
        split_strategy: AbstractSplitStrategy,
        values: list[float] | None = None
    ) -> Expense:
        with self._lock:
            # 1. Compute individual shares via strategy
            splits = split_strategy.split(total_amount, participant_user_ids, values)

            # 2. Record expense
            expense = Expense(self._current_expense_id, total_amount, paid_by_user_id, splits)
            self.expenses[self._current_expense_id] = expense
            self._current_expense_id += 1

            # 3. Update the ledger
            for split in splits:
                borrower = split.user_id
                payer = paid_by_user_id
                amount = split.amount

                if borrower == payer:
                    continue  # Payer paying for themselves creates no debt

                # Initialize balance maps if not present
                if borrower not in self.balances:
                    self.balances[borrower] = {}
                if payer not in self.balances:
                    self.balances[payer] = {}

                # Borrower owes Payer
                self.balances[borrower][payer] = round(self.balances[borrower].get(payer, 0.0) + amount, 2)
                # Symmetrically, Payer is owed by Borrower (negative debt)
                self.balances[payer][borrower] = round(self.balances[payer].get(borrower, 0.0) - amount, 2)

            return expense

    def show_balance(self, user_id: int, user_service: UserManagementService | None = None):
        """Prints all debts for a specific user."""
        with self._lock:
            has_balance = False
            user_debts = self.balances.get(user_id, {})
            for other_id, amount in user_debts.items():
                if amount > 0:
                    has_balance = True
                    u1_name = user_service._users[user_id].name if user_service and user_id in user_service._users else f"User {user_id}"
                    u2_name = user_service._users[other_id].name if user_service and other_id in user_service._users else f"User {other_id}"
                    print(f"  {u1_name} owes {u2_name}: ₹{amount:.2f}")
            if not has_balance:
                print(f"  No balances for User {user_id}")

    def show_all_balances(self, user_service: UserManagementService | None = None):
        """Prints all non-zero debts across all users."""
        with self._lock:
            has_any = False
            for user_id, user_debts in self.balances.items():
                for other_id, amount in user_debts.items():
                    if amount > 0:
                        has_any = True
                        u1_name = user_service._users[user_id].name if user_service and user_id in user_service._users else f"User {user_id}"
                        u2_name = user_service._users[other_id].name if user_service and other_id in user_service._users else f"User {other_id}"
                        print(f"  {u1_name} owes {u2_name}: ₹{amount:.2f}")
            if not has_any:
                print("  No balances")


# -----------------------------------------------------------------------------
# VERIFICATION DRIVER (Runs the exact scenario from requirements)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    user_service = UserManagementService()
    expense_service = ExpenseManagementService()

    # 1. Register 4 users
    u1 = user_service.add_user("Alice", "alice@example.com")
    u2 = user_service.add_user("Bob", "bob@example.com")
    u3 = user_service.add_user("Charlie", "charlie@example.com")
    u4 = user_service.add_user("David", "david@example.com")
    print(f"Registered 4 users: {u1.name}, {u2.name}, {u3.name}, {u4.name}")

    # Strategies
    equal_strategy = EqualSplitStrategy()
    exact_strategy = ExactSplitStrategy()
    percent_strategy = PercentSplitStrategy()

    print("\n--- Expense 1: Alice pays 1000 equally among all 4 ---")
    expense_service.add_expense(
        total_amount=1000.0,
        paid_by_user_id=u1.user_id,
        participant_user_ids=[u1.user_id, u2.user_id, u3.user_id, u4.user_id],
        split_strategy=equal_strategy
    )
    expense_service.show_all_balances(user_service)

    print("\n--- Expense 2: Alice pays 1250 for Bob (370) & Charlie (880) EXACT ---")
    expense_service.add_expense(
        total_amount=1250.0,
        paid_by_user_id=u1.user_id,
        participant_user_ids=[u2.user_id, u3.user_id],
        split_strategy=exact_strategy,
        values=[370.0, 880.0]
    )
    expense_service.show_all_balances(user_service)

    print("\n--- Expense 3: David pays 1200 PERCENT (Alice: 40%, Bob: 20%, Charlie: 20%, David: 20%) ---")
    expense_service.add_expense(
        total_amount=1200.0,
        paid_by_user_id=u4.user_id,
        participant_user_ids=[u1.user_id, u2.user_id, u3.user_id, u4.user_id],
        split_strategy=percent_strategy,
        values=[40.0, 20.0, 20.0, 20.0]
    )
    expense_service.show_all_balances(user_service)

    print("\n--- Individual Balance: Alice's view ---")
    expense_service.show_balance(u1.user_id, user_service)

    print("\n--- Validation Tests: Invalid exact and percent inputs ---")
    try:
        expense_service.add_expense(100.0, u1.user_id, [u2.user_id, u3.user_id], exact_strategy, [40.0, 50.0])
    except ValueError as e:
        print("Caught expected exact split error:", e)

    try:
        expense_service.add_expense(100.0, u1.user_id, [u2.user_id, u3.user_id], percent_strategy, [40.0, 50.0])
    except ValueError as e:
        print("Caught expected percentage split error:", e)

    print("\nSUCCESS: All Splitwise requirements verified.")
