"""Aplicacao de teste: E-commerce com assinatura/entitlement."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class User:
    user_id: str
    role: str  # client | admin
    premium_enabled: bool = False


@dataclass
class EcommerceSubscriptionApp:
    users: dict[str, User] = field(default_factory=dict)
    catalog: dict[str, int] = field(default_factory=lambda: {"ebook-sec": 120_00, "curso-appsec": 300_00})
    carts: dict[str, list[str]] = field(default_factory=dict)
    coupons: dict[str, int] = field(default_factory=lambda: {"SAVE10": 10})
    subscriptions: dict[str, str] = field(default_factory=dict)
    payments: dict[str, str] = field(default_factory=dict)
    payment_owner: dict[str, str] = field(default_factory=dict)
    payment_amount_cents: dict[str, int] = field(default_factory=dict)
    audit: list[str] = field(default_factory=list)
    used_coupons_by_user: dict[str, set[str]] = field(default_factory=dict)
    processed_webhook_events: set[str] = field(default_factory=set)

    def register(self, user_id: str, role: str) -> User:
        user = User(user_id=user_id, role=role)
        self.users[user_id] = user
        self.carts[user_id] = []
        self.used_coupons_by_user[user_id] = set()
        self.audit.append(f"register:{user_id}:{role}")
        return user

    def login(self, user_id: str) -> User:
        if user_id not in self.users:
            raise ValueError("usuario nao encontrado")
        self.audit.append(f"login:{user_id}")
        return self.users[user_id]

    def add_to_cart(self, actor: User, sku: str) -> None:
        if sku not in self.catalog:
            raise ValueError("sku invalido")
        self.carts[actor.user_id].append(sku)
        self.audit.append(f"cart_add:{actor.user_id}:{sku}")

    def checkout(self, actor: User, coupon_code: str | None = None) -> tuple[str, int]:
        total = sum(self.catalog[sku] for sku in self.carts[actor.user_id])
        if coupon_code:
            if "," in coupon_code:
                self.audit.append(f"coupon_blocked_stacking:{actor.user_id}:{coupon_code}")
                raise ValueError("empilhamento de cupom nao permitido")
            if coupon_code in self.used_coupons_by_user[actor.user_id]:
                self.audit.append(f"coupon_blocked_reuse:{actor.user_id}:{coupon_code}")
                raise ValueError("reutilizacao abusiva de cupom")
            discount = self.coupons.get(coupon_code, 0)
            total = total - int(total * (discount / 100))
            self.used_coupons_by_user[actor.user_id].add(coupon_code)
            self.audit.append(f"coupon_applied:{actor.user_id}:{coupon_code}:{discount}")
        payment_id = f"pay-{len(self.payments)+1}"
        self.payments[payment_id] = "pending"
        self.payment_owner[payment_id] = actor.user_id
        self.payment_amount_cents[payment_id] = total
        self.audit.append(f"checkout:{actor.user_id}:{payment_id}:{total}")
        return payment_id, total

    def activate_subscription(self, actor: User, plan: str) -> None:
        self.subscriptions[actor.user_id] = plan
        actor.premium_enabled = False  # aguarda webhook de pagamento
        self.audit.append(f"subscription_activate:{actor.user_id}:{plan}")

    def cancel_subscription(self, actor: User) -> None:
        self.subscriptions[actor.user_id] = "cancelled"
        actor.premium_enabled = False
        self.audit.append(f"subscription_cancel:{actor.user_id}")

    def payment_webhook(
        self,
        payment_id: str,
        user_id: str,
        status: str,
        signature_ok: bool,
        webhook_event_id: str,
    ) -> None:
        if not signature_ok:
            self.audit.append(f"webhook_blocked_bad_signature:{payment_id}:{user_id}")
            raise PermissionError("assinatura webhook invalida")
        if webhook_event_id in self.processed_webhook_events:
            self.audit.append(f"webhook_blocked_replay:{payment_id}:{webhook_event_id}")
            raise ValueError("replay de webhook detectado")
        if self.payment_owner.get(payment_id) != user_id:
            self.audit.append(f"webhook_blocked_owner_mismatch:{payment_id}:{user_id}")
            raise PermissionError("owner de pagamento inconsistente")
        if status == "paid" and self.payment_amount_cents.get(payment_id, 0) <= 0:
            self.audit.append(f"webhook_blocked_invalid_amount:{payment_id}:{user_id}")
            raise ValueError("pagamento invalido para liberar entitlement")
        self.payments[payment_id] = status
        if status == "paid" and self.subscriptions.get(user_id) not in {None, "cancelled"}:
            self.users[user_id].premium_enabled = True
        self.processed_webhook_events.add(webhook_event_id)
        self.audit.append(f"webhook:{payment_id}:{user_id}:{status}:{webhook_event_id}")

    def premium_content(self, actor: User) -> str:
        if actor.role != "admin" and not actor.premium_enabled:
            raise PermissionError("entitlement premium ausente")
        return "conteudo_premium_liberado"


def run_smoke() -> None:
    app = EcommerceSubscriptionApp()
    admin = app.register("adm-1", "admin")
    client = app.register("cli-1", "client")
    app.login(client.user_id)
    app.add_to_cart(client, "ebook-sec")
    app.add_to_cart(client, "curso-appsec")
    payment_id, _ = app.checkout(client, "SAVE10")
    app.activate_subscription(client, "gold")
    try:
        app.premium_content(client)
        raise AssertionError("nao deveria liberar antes do pagamento")
    except PermissionError:
        pass
    app.payment_webhook(payment_id, client.user_id, "paid", signature_ok=True, webhook_event_id="evt-1")
    try:
        app.payment_webhook(payment_id, client.user_id, "paid", signature_ok=True, webhook_event_id="evt-1")
        raise AssertionError("deveria bloquear replay de webhook")
    except ValueError:
        pass
    assert app.premium_content(client) == "conteudo_premium_liberado"
    try:
        app.checkout(client, "SAVE10")
        raise AssertionError("deveria bloquear reutilizacao de cupom")
    except ValueError:
        pass
    app.cancel_subscription(client)
    try:
        app.premium_content(client)
        raise AssertionError("deveria revogar entitlement no cancelamento")
    except PermissionError:
        pass
    assert app.premium_content(admin) == "conteudo_premium_liberado"
    assert any("webhook_blocked_replay" in item for item in app.audit)
    assert any("coupon_blocked_reuse" in item for item in app.audit)
    print("ecommerce_smoke_ok")


if __name__ == "__main__":
    run_smoke()
