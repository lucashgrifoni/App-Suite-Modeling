"""Aplicacao de teste: Financas pessoais / carteira digital.

Escopo controlado para validacao local de fluxos criticos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import csv


@dataclass
class User:
    user_id: str
    role: str  # user | admin
    name: str


@dataclass
class Account:
    account_id: str
    owner_user_id: str
    balance_cents: int


@dataclass
class Transaction:
    tx_id: str
    from_account_id: str
    to_account_id: str
    amount_cents: int
    category: str
    created_at: str
    status: str


@dataclass
class FinanceApp:
    users: dict[str, User] = field(default_factory=dict)
    accounts: dict[str, Account] = field(default_factory=dict)
    transactions: list[Transaction] = field(default_factory=list)
    audit_log: list[str] = field(default_factory=list)
    transfer_request_ids: set[str] = field(default_factory=set)
    processed_webhook_events: set[str] = field(default_factory=set)

    def register(self, user_id: str, role: str, name: str) -> User:
        user = User(user_id=user_id, role=role, name=name)
        self.users[user_id] = user
        self.audit_log.append(f"register:{user_id}:{role}")
        return user

    def login(self, user_id: str) -> User:
        if user_id not in self.users:
            raise ValueError("usuario nao encontrado")
        self.audit_log.append(f"login:{user_id}")
        return self.users[user_id]

    def create_account(self, account_id: str, owner_user_id: str, initial_cents: int) -> Account:
        account = Account(account_id=account_id, owner_user_id=owner_user_id, balance_cents=initial_cents)
        self.accounts[account_id] = account
        self.audit_log.append(f"create_account:{account_id}:{owner_user_id}:{initial_cents}")
        return account

    def get_balance(self, actor: User, account_id: str) -> int:
        account = self.accounts[account_id]
        if actor.role != "admin" and account.owner_user_id != actor.user_id:
            raise PermissionError("acesso negado ao saldo")
        self.audit_log.append(f"balance_read:{actor.user_id}:{account_id}")
        return account.balance_cents

    def transfer(
        self,
        actor: User,
        from_account_id: str,
        to_account_id: str,
        amount_cents: int,
        category: str,
        transfer_request_id: str,
    ) -> Transaction:
        if amount_cents <= 0:
            raise ValueError("valor invalido")
        if transfer_request_id in self.transfer_request_ids:
            self.audit_log.append(f"transfer_blocked_duplicate_request:{actor.user_id}:{transfer_request_id}")
            raise ValueError("dupla submissao detectada")
        from_account = self.accounts[from_account_id]
        to_account = self.accounts[to_account_id]
        if actor.role != "admin" and from_account.owner_user_id != actor.user_id:
            self.audit_log.append(f"transfer_blocked_unauthorized:{actor.user_id}:{from_account_id}")
            raise PermissionError("nao autorizado a transferir desta conta")
        if from_account.balance_cents < amount_cents:
            self.audit_log.append(f"transfer_blocked_insufficient_funds:{actor.user_id}:{from_account_id}")
            raise ValueError("saldo insuficiente")

        from_account.balance_cents -= amount_cents
        to_account.balance_cents += amount_cents
        self.transfer_request_ids.add(transfer_request_id)
        tx = Transaction(
            tx_id=f"tx-{len(self.transactions)+1}",
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount_cents=amount_cents,
            category=category,
            created_at=datetime.now(timezone.utc).isoformat(),
            status="pending_webhook_confirmation",
        )
        self.transactions.append(tx)
        self.audit_log.append(
            f"transfer:{actor.user_id}:{from_account_id}:{to_account_id}:{amount_cents}:{category}:{transfer_request_id}"
        )
        return tx

    def payment_webhook(self, tx_id: str, status: str, mock_signature_ok: bool, webhook_event_id: str) -> None:
        if not mock_signature_ok:
            self.audit_log.append(f"webhook_blocked_bad_signature:{tx_id}")
            raise PermissionError("assinatura de webhook invalida")
        if webhook_event_id in self.processed_webhook_events:
            self.audit_log.append(f"webhook_blocked_replay:{tx_id}:{webhook_event_id}")
            raise ValueError("replay de webhook detectado")
        tx = next(t for t in self.transactions if t.tx_id == tx_id)
        if tx.status == "confirmed" and status != "confirmed":
            self.audit_log.append(f"webhook_blocked_state_regression:{tx_id}:{status}")
            raise ValueError("regressao de estado invalida")
        tx.status = status
        self.processed_webhook_events.add(webhook_event_id)
        self.audit_log.append(f"webhook:{tx_id}:{status}:{webhook_event_id}")

    def transaction_history(self, actor: User, account_id: str) -> list[Transaction]:
        account = self.accounts[account_id]
        if actor.role != "admin" and account.owner_user_id != actor.user_id:
            raise PermissionError("acesso negado ao historico")
        data = [
            t
            for t in self.transactions
            if t.from_account_id == account_id or t.to_account_id == account_id
        ]
        self.audit_log.append(f"history_read:{actor.user_id}:{account_id}:{len(data)}")
        return data

    def export_statement_csv(self, actor: User, account_id: str, output: Path) -> Path:
        history = self.transaction_history(actor, account_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(["tx_id", "from_account_id", "to_account_id", "amount_cents", "category", "status"])
            for tx in history:
                writer.writerow(
                    [tx.tx_id, tx.from_account_id, tx.to_account_id, tx.amount_cents, tx.category, tx.status]
                )
        self.audit_log.append(f"export_statement:{actor.user_id}:{account_id}:{output}")
        return output


def run_smoke() -> None:
    app = FinanceApp()
    admin = app.register("admin-1", "admin", "Administrador")
    alice = app.register("user-1", "user", "Alice")
    bob = app.register("user-2", "user", "Bob")
    app.create_account("acc-alice", alice.user_id, 500_00)
    app.create_account("acc-bob", bob.user_id, 100_00)
    app.login(alice.user_id)
    tx = app.transfer(alice, "acc-alice", "acc-bob", 150_00, "moradia", "req-1")
    app.payment_webhook(tx.tx_id, "confirmed", mock_signature_ok=True, webhook_event_id="evt-1")
    try:
        app.payment_webhook(tx.tx_id, "confirmed", mock_signature_ok=True, webhook_event_id="evt-1")
        raise AssertionError("deveria bloquear replay")
    except ValueError:
        pass
    try:
        app.transfer(alice, "acc-alice", "acc-bob", 150_00, "moradia", "req-1")
        raise AssertionError("deveria bloquear dupla submissao")
    except ValueError:
        pass
    try:
        app.export_statement_csv(bob, "acc-alice", Path("artifacts/test-app-validation/finance/forbidden.csv"))
        raise AssertionError("deveria bloquear extrato de outro usuario")
    except PermissionError:
        pass
    assert app.get_balance(admin, "acc-alice") == 350_00
    assert app.get_balance(admin, "acc-bob") == 250_00
    app.export_statement_csv(alice, "acc-alice", Path("artifacts/test-app-validation/finance/statement.csv"))
    assert any("transfer_blocked_duplicate_request" in item for item in app.audit_log)
    assert any("webhook_blocked_replay" in item for item in app.audit_log)
    print("finance_smoke_ok")


if __name__ == "__main__":
    run_smoke()
