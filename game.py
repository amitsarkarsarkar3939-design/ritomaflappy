"""Flappy Friends desktop game and loopback-only Razorpay payment helper."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import html
import json
import math
import os
import random
import re
import secrets
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, X, Y, Canvas, StringVar, Tk, ttk
from tkinter import messagebox
from typing import Any


ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("FLAPPY_DB_PATH", ROOT / "flappy-friends.sqlite3"))
HOST = "127.0.0.1"
PORT = int(os.environ.get("FLAPPY_PORT", "8765"))
VALID_MODES = {"classic", "chill", "speedy", "horror", "fun", "extreme"}
SKINS: dict[str, dict[str, str]] = {
    "Sunny": {"sky": "#87dff2", "hill": "#8bd5a5", "ground": "#55ae76", "pipe": "#45b96c", "bird": "#ffd34d", "coin": "#ffc83d"},
    "Sunset": {"sky": "#fa967e", "hill": "#c77f8b", "ground": "#875578", "pipe": "#d76e59", "bird": "#ffda73", "coin": "#ffe16b"},
    "Midnight": {"sky": "#1b2b58", "hill": "#4c648b", "ground": "#263b68", "pipe": "#399d9b", "bird": "#b9e5ff", "coin": "#ffe178"},
    "Spooky": {"sky": "#171829", "hill": "#39304e", "ground": "#201e38", "pipe": "#7762a6", "bird": "#d4c2ff", "coin": "#b8f17d"},
    "Party": {"sky": "#ffb5d5", "hill": "#a7e4c4", "ground": "#65bd9b", "pipe": "#ed79b7", "bird": "#fff07c", "coin": "#ffe34a"},
}
class PaymentError(Exception):
    """A safe, user-facing payment provider error."""


class PaymentConfigurationError(PaymentError):
    """Required merchant settings are missing or unsafe."""


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args: Any) -> Any:
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def initialize_database(path: Path | None = None) -> None:
    global DB_PATH
    if path is not None:
        DB_PATH = path
    schema = (ROOT / "data.sql").read_text(encoding="utf-8")
    with connect_db() as connection:
        connection.executescript(schema)
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(purchases)")
        }
        if "provider_order_id" not in columns:
            connection.execute("ALTER TABLE purchases ADD COLUMN provider_order_id TEXT")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS purchases_provider_order "
            "ON purchases (provider_order_id)"
        )


def razorpay_settings() -> tuple[str, str]:
    key_id = os.environ.get("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
    if not key_id or not key_secret:
        raise PaymentConfigurationError(
            "Razorpay merchant keys are not configured. Set RAZORPAY_KEY_ID and "
            "RAZORPAY_KEY_SECRET in PowerShell, then restart the game."
        )
    if key_id.startswith("rzp_live_") and os.environ.get("RAZORPAY_LIVE_PAYMENTS") != "YES":
        raise PaymentConfigurationError(
            "Live payments are disabled. Set RAZORPAY_LIVE_PAYMENTS=YES only after "
            "your Razorpay merchant account is approved and test payments work."
        )
    if not key_id.startswith(("rzp_test_", "rzp_live_")):
        raise PaymentConfigurationError(
            "Use the Key ID from your Razorpay Dashboard (it starts with rzp_test_ or rzp_live_)."
        )
    return key_id, key_secret


def _razorpay_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    key_id, key_secret = razorpay_settings()
    credentials = base64.b64encode(f"{key_id}:{key_secret}".encode("utf-8")).decode("ascii")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"https://api.razorpay.com/v1/{path.lstrip('/')}",
        data=body,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read(131072))
    except urllib.error.HTTPError as error:
        error.read(2048)
        raise PaymentError(f"Razorpay could not complete the request (HTTP {error.code}).") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise PaymentError("Razorpay could not be reached. Please try again.") from error
    if not isinstance(result, dict):
        raise PaymentError("Razorpay returned an invalid response.")
    return result


def create_razorpay_order(pack_id: str) -> dict[str, Any]:
    key_id, _ = razorpay_settings()
    with connect_db() as connection:
        pack = connection.execute(
            "SELECT pack_id, display_name, coins, price_paise FROM store_packs "
            "WHERE pack_id = ? AND enabled = 1",
            (pack_id,),
        ).fetchone()
    if pack is None:
        raise ValueError("That coin pack is not available.")

    merchant_order_id = f"FFF{uuid.uuid4().hex[:24].upper()}"
    order = _razorpay_request("POST", "orders", {
        "amount": int(pack["price_paise"]),
        "currency": "INR",
        "receipt": merchant_order_id,
        "notes": {"pack_id": pack_id, "coins": str(pack["coins"])},
    })
    provider_order_id = order.get("id")
    if (
        not isinstance(provider_order_id, str)
        or not provider_order_id.startswith("order_")
        or order.get("amount") != int(pack["price_paise"])
        or order.get("currency") != "INR"
    ):
        raise PaymentError("Razorpay returned an order that did not match the selected coin pack.")

    with connect_db() as connection:
        connection.execute(
            "INSERT INTO purchases "
            "(merchant_order_id, provider_order_id, pack_id, amount_paise, coins, state) "
            "VALUES (?, ?, ?, ?, ?, 'PENDING')",
            (
                merchant_order_id,
                provider_order_id,
                pack["pack_id"],
                pack["price_paise"],
                pack["coins"],
            ),
        )
    return {
        "merchant_order_id": merchant_order_id,
        "checkout_url": f"http://{HOST}:{PORT}/checkout?order={merchant_order_id}",
        "provider_order_id": provider_order_id,
        "key_id": key_id,
        "coins": int(pack["coins"]),
        "price_paise": int(pack["price_paise"]),
        "environment": "test" if key_id.startswith("rzp_test_") else "live",
    }


def _purchase_result(merchant_order_id: str) -> dict[str, Any]:
    with connect_db() as connection:
        purchase = connection.execute(
            "SELECT merchant_order_id, coins, state FROM purchases WHERE merchant_order_id = ?",
            (merchant_order_id,),
        ).fetchone()
        balance = connection.execute(
            "SELECT coin_balance FROM profile WHERE id = 1"
        ).fetchone()["coin_balance"]
    if purchase is None:
        raise ValueError("Order not found.")
    return {
        "merchant_order_id": purchase["merchant_order_id"],
        "state": purchase["state"],
        "coins": purchase["coins"],
        "balance": balance,
    }


def _fetch_verified_payment(
    merchant_order_id: str,
    provider_order_id: str,
    payment_id: str,
) -> dict[str, Any]:
    payment = _razorpay_request("GET", f"payments/{urllib.parse.quote(payment_id, safe='')}")
    with connect_db() as connection:
        purchase = connection.execute(
            "SELECT amount_paise, state FROM purchases WHERE merchant_order_id = ?",
            (merchant_order_id,),
        ).fetchone()
    if purchase is None:
        raise ValueError("Order not found.")
    if (
        payment.get("order_id") != provider_order_id
        or payment.get("amount") != purchase["amount_paise"]
        or payment.get("currency") != "INR"
    ):
        raise PaymentError("The Razorpay payment does not match this order and amount.")
    if payment.get("status") == "captured" and payment.get("captured") is True:
        transaction_id = payment.get("id")
        if not isinstance(transaction_id, str):
            raise PaymentError("Razorpay returned a captured payment without a transaction ID.")
        with connect_db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                "UPDATE purchases SET state = 'COMPLETED', provider_transaction_id = ?, "
                "completed_at = CURRENT_TIMESTAMP "
                "WHERE merchant_order_id = ? AND provider_order_id = ? "
                "AND state = 'PENDING' AND amount_paise = ?",
                (transaction_id, merchant_order_id, provider_order_id, purchase["amount_paise"]),
            ).rowcount
            if changed == 1:
                coins = connection.execute(
                    "SELECT coins FROM purchases WHERE merchant_order_id = ?",
                    (merchant_order_id,),
                ).fetchone()["coins"]
                connection.execute(
                    "UPDATE profile SET coin_balance = coin_balance + ? WHERE id = 1",
                    (coins,),
                )
                connection.execute(
                    "INSERT INTO wallet_ledger (entry_type, coin_delta, reference_id) "
                    "VALUES ('PURCHASE', ?, ?)",
                    (coins, merchant_order_id),
                )
    elif payment.get("status") == "authorized":
        with connect_db() as connection:
            connection.execute(
                "UPDATE purchases SET provider_transaction_id = ? "
                "WHERE merchant_order_id = ? AND state = 'PENDING'",
                (payment_id, merchant_order_id),
            )
    return _purchase_result(merchant_order_id)


def verify_razorpay_payment(
    merchant_order_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if (
        len(merchant_order_id) != 27
        or not merchant_order_id.startswith("FFF")
        or not all(char in "0123456789ABCDEF" for char in merchant_order_id[3:])
    ):
        raise ValueError("Invalid order ID.")
    with connect_db() as connection:
        purchase = connection.execute(
            "SELECT merchant_order_id, provider_order_id, state "
            "FROM purchases WHERE merchant_order_id = ?",
            (merchant_order_id,),
        ).fetchone()
    if purchase is None:
        raise ValueError("Order not found.")
    if purchase["state"] == "COMPLETED":
        return _purchase_result(merchant_order_id)
    provider_order_id = purchase["provider_order_id"]
    payment_id = payload.get("razorpay_payment_id")
    returned_order_id = payload.get("razorpay_order_id")
    signature = payload.get("razorpay_signature")
    if (
        not isinstance(payment_id, str)
        or not payment_id.startswith("pay_")
        or not payment_id.isascii()
        or not all(char.isalnum() or char == "_" for char in payment_id)
        or not isinstance(returned_order_id, str)
        or len(returned_order_id) > 128
        or not isinstance(signature, str)
        or len(signature) != 64
        or not all(char in "0123456789abcdefABCDEF" for char in signature)
    ):
        raise ValueError("Razorpay returned an incomplete payment response.")
    if provider_order_id is None or returned_order_id != provider_order_id:
        raise PaymentError("The payment does not belong to this order.")
    _, key_secret = razorpay_settings()
    expected_signature = hmac.new(
        key_secret.encode("utf-8"),
        f"{provider_order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        raise PaymentError("Razorpay payment signature verification failed.")
    return _fetch_verified_payment(merchant_order_id, provider_order_id, payment_id)


def refresh_purchase(merchant_order_id: str) -> dict[str, Any]:
    if not merchant_order_id.startswith("FFF") or len(merchant_order_id) != 27:
        raise ValueError("Invalid order ID.")
    with connect_db() as connection:
        purchase = connection.execute(
            "SELECT provider_order_id, provider_transaction_id, state "
            "FROM purchases WHERE merchant_order_id = ?",
            (merchant_order_id,),
        ).fetchone()
    if purchase is None:
        raise ValueError("Order not found.")
    if purchase["state"] == "PENDING" and purchase["provider_order_id"]:
        provider_order_id = purchase["provider_order_id"]
        order_payments = _razorpay_request(
            "GET",
            f"orders/{urllib.parse.quote(provider_order_id, safe='')}/payments",
        )
        payments = order_payments.get("items")
        matching_payments = [
            payment for payment in payments
            if isinstance(payment, dict)
            and payment.get("order_id") == provider_order_id
            and payment.get("currency") == "INR"
            and payment.get("status") in {"authorized", "captured"}
            and isinstance(payment.get("id"), str)
        ] if isinstance(payments, list) else []
        matching_payments.sort(key=lambda payment: payment["status"] != "captured")
        payment_id = matching_payments[0]["id"] if matching_payments else None
        if payment_id:
            with connect_db() as connection:
                connection.execute(
                    "UPDATE purchases SET provider_transaction_id = ? "
                    "WHERE merchant_order_id = ? AND state = 'PENDING'",
                    (payment_id, merchant_order_id),
                )
        if payment_id:
            return _fetch_verified_payment(merchant_order_id, provider_order_id, payment_id)
    return _purchase_result(merchant_order_id)


def api_response(handler: BaseHTTPRequestHandler, status: int, data: dict[str, Any]) -> None:
    payload = json.dumps(data).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    origin = handler.headers.get("Origin")
    allowed_origins = {
        f"http://{HOST}:{PORT}",
        f"http://localhost:{PORT}",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    }
    if origin in allowed_origins:
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        handler.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        handler.send_header("Vary", "Origin")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _password_digest(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)


def _issue_session(user_id: int, username: str) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + 30 * 24 * 60 * 60
    with connect_db() as connection:
        connection.execute("DELETE FROM user_sessions WHERE expires_at <= ?", (int(time.time()),))
        connection.execute(
            "INSERT INTO user_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (hashlib.sha256(token.encode("ascii")).hexdigest(), user_id, expires_at),
        )
        connection.execute("INSERT OR IGNORE INTO user_saves (user_id) VALUES (?)", (user_id,))
    return {"token": token, "username": username, "expires_at": expires_at}


def _authenticated_user(handler: BaseHTTPRequestHandler) -> tuple[int, str] | None:
    authorization = handler.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not 20 <= len(token) <= 128:
        return None
    token_hash = hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()
    with connect_db() as connection:
        row = connection.execute(
            "SELECT a.user_id, a.username FROM user_sessions s "
            "JOIN user_accounts a ON a.user_id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > ?",
            (token_hash, int(time.time())),
        ).fetchone()
    return (int(row["user_id"]), str(row["username"])) if row is not None else None


class GameApiHandler(BaseHTTPRequestHandler):
    server_version = "FlappyFriendsLocal/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[local-api] {self.address_string()} {format % args}")

    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin")
        allowed_origins = {
            f"http://{HOST}:{PORT}",
            f"http://localhost:{PORT}",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        }
        if origin not in allowed_origins:
            api_response(self, 403, {"error": "Cross-origin requests are not allowed."})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/api/health":
            api_response(self, 200, {"ok": True})
            return
        if parsed.path == "/api/state":
            account = _authenticated_user(self)
            if account is None:
                api_response(self, 401, {"error": "Sign in to load your saved game."})
                return
            with connect_db() as connection:
                row = connection.execute(
                    "SELECT state_json, updated_at FROM user_saves WHERE user_id = ?",
                    (account[0],),
                ).fetchone()
            api_response(self, 200, {
                "state": json.loads(row["state_json"]),
                "updated_at": row["updated_at"],
            })
            return
        if parsed.path == "/checkout":
            order_id = urllib.parse.parse_qs(parsed.query).get("order", [""])[0]
            try:
                page = self._checkout_page(order_id)
            except (ValueError, PaymentError) as error:
                self._send_html(400, self._message_page("Checkout unavailable", str(error)))
            else:
                self._send_html(200, page)
            return
        if parsed.path == "/api/modes":
            with connect_db() as connection:
                modes = [dict(row) for row in connection.execute(
                    "SELECT mode_id, display_name, description, gravity, flap_strength, "
                    "pipe_gap, pipe_speed, spawn_interval FROM game_modes ORDER BY rowid"
                )]
            api_response(self, 200, {"modes": modes})
            return
        if parsed.path == "/api/catalog":
            with connect_db() as connection:
                packs = [dict(row) for row in connection.execute(
                    "SELECT pack_id, display_name, coins, price_paise FROM store_packs "
                    "WHERE enabled = 1 ORDER BY price_paise, coins"
                )]
            api_response(self, 200, {"packs": packs})
            return
        if parsed.path == "/api/profile":
            mode = urllib.parse.parse_qs(parsed.query).get("mode", ["classic"])[0]
            if mode not in VALID_MODES:
                api_response(self, 400, {"error": "Unknown game mode."})
                return
            with connect_db() as connection:
                row = connection.execute(
                    "SELECT p.coin_balance, b.score AS best "
                    "FROM profile p JOIN best_scores b ON b.mode_id = ? WHERE p.id = 1",
                    (mode,),
                ).fetchone()
            api_response(self, 200, {"balance": row["coin_balance"], "best": row["best"]})
            return
        if parsed.path.startswith("/api/purchase/"):
            order_id = parsed.path.rsplit("/", 1)[-1]
            try:
                result = refresh_purchase(order_id)
            except ValueError as error:
                api_response(self, 404, {"error": str(error)})
            except PaymentError as error:
                api_response(self, 503, {"error": str(error)})
            else:
                api_response(self, 200, result)
            return
        api_response(self, 404, {"error": "Not found."})

    def _checkout_page(self, merchant_order_id: str) -> str:
        if not merchant_order_id.startswith("FFF") or len(merchant_order_id) != 27:
            raise ValueError("Invalid checkout order.")
        key_id, _ = razorpay_settings()
        with connect_db() as connection:
            purchase = connection.execute(
                "SELECT p.provider_order_id, p.amount_paise, p.state, s.display_name "
                "FROM purchases p JOIN store_packs s ON s.pack_id = p.pack_id "
                "WHERE p.merchant_order_id = ?",
                (merchant_order_id,),
            ).fetchone()
        if purchase is None or purchase["provider_order_id"] is None:
            raise ValueError("Checkout order not found.")
        if purchase["state"] != "PENDING":
            raise ValueError("This checkout order is no longer pending.")
        options = {
            "key": key_id,
            "amount": int(purchase["amount_paise"]),
            "currency": "INR",
            "name": "Flappy Friends",
            "description": str(purchase["display_name"]),
            "order_id": purchase["provider_order_id"],
            "theme": {"color": "#365f9d"},
        }
        options_json = json.dumps(options).replace("<", "\\u003c")
        verify_path = json.dumps(f"/api/purchase/{merchant_order_id}/verify")
        return (
            "<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Flappy Friends - secure checkout</title>"
            "<body style='font:16px system-ui;max-width:520px;margin:12vh auto;padding:24px;"
            "color:#263d66;background:#f2f8ff'>"
            "<main style='background:white;border-radius:20px;padding:24px;box-shadow:0 12px 36px #263d6620'>"
            "<p style='color:#e58b39;font-size:12px;font-weight:bold;letter-spacing:.12em'>FLAPPY FRIENDS</p>"
            "<h1>Buy coins</h1><p>Complete your payment securely with Razorpay.</p>"
            "<button id='pay' style='width:100%;padding:14px;border:0;border-radius:12px;"
            "background:#365f9d;color:white;font-size:16px;font-weight:bold;cursor:pointer'>"
            "Continue to payment</button><p id='status' role='status'></p>"
            "<p style='font-size:12px;color:#66758c'>Coins are added only after the payment is verified.</p>"
            "</main><script src='https://checkout.razorpay.com/v1/checkout.js'></script>"
            "<script>const options="
            + options_json
            + ";options.handler=async function(response){"
            "const status=document.getElementById('status');status.textContent='Verifying payment…';"
            "try{const result=await fetch("
            + verify_path
            + ",{method:'POST',headers:{'Content-Type':'application/json'},"
            "body:JSON.stringify(response)});const data=await result.json();"
            "if(!result.ok)throw new Error(data.error||'Payment verification failed.');"
            "status.textContent=data.state==='COMPLETED'?'Payment verified! Coins were added.':'Payment received; waiting for capture confirmation.';"
            "}catch(error){status.textContent=error.message;}};"
            "options.modal={ondismiss:function(){document.getElementById('status').textContent='Checkout closed. You can try again.';}};"
            "document.getElementById('pay').addEventListener('click',function(){"
            "if(!window.Razorpay){document.getElementById('status').textContent='Could not load Razorpay checkout. Check your internet connection.';return;}"
            "new Razorpay(options).open();});</script></body></html>"
        )

    @staticmethod
    def _message_page(title: str, message: str) -> str:
        return (
            "<!doctype html><meta charset='utf-8'><meta name='viewport' "
            "content='width=device-width,initial-scale=1'><title>"
            + html.escape(title)
            + "</title><body style='font:16px system-ui;max-width:520px;margin:12vh auto;padding:24px'>"
            "<h1>" + html.escape(title) + "</h1><p>" + html.escape(message) + "</p></body>"
        )

    def _send_html(self, status: int, page: str) -> None:
        payload = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        verifying_order = None
        if parsed.path.startswith("/api/purchase/") and parsed.path.endswith("/verify"):
            verifying_order = parsed.path.removeprefix("/api/purchase/").removesuffix("/verify").strip("/")
        allowed_paths = {
            "/api/run", "/api/purchase", "/api/auth/signup",
            "/api/auth/signin", "/api/auth/signout",
        }
        if parsed.path not in allowed_paths and verifying_order is None:
            api_response(self, 404, {"error": "Not found."})
            return
        origin = self.headers.get("Origin")
        allowed_origins = {
            f"http://{HOST}:{PORT}",
            f"http://localhost:{PORT}",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        }
        if origin is not None and origin not in allowed_origins:
            api_response(self, 403, {"error": "Cross-origin requests are not allowed."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            maximum_length = 65536 if parsed.path == "/api/state" else 8192
            if not 1 <= length <= maximum_length:
                raise ValueError(f"Request body must be between 1 and {maximum_length} bytes.")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object.")
            if self.path == "/api/run":
                self._save_run(body)
            elif parsed.path == "/api/purchase":
                self._new_purchase(body)
            elif parsed.path == "/api/auth/signup":
                self._sign_up(body)
            elif parsed.path == "/api/auth/signin":
                self._sign_in(body)
            elif parsed.path == "/api/auth/signout":
                self._sign_out()
            else:
                self._verify_purchase(verifying_order or "", body)
        except (ValueError, json.JSONDecodeError) as error:
            api_response(self, 400, {"error": str(error)})

    def do_PUT(self) -> None:
        if urllib.parse.urlsplit(self.path).path != "/api/state":
            api_response(self, 404, {"error": "Not found."})
            return
        origin = self.headers.get("Origin")
        allowed_origins = {
            f"http://{HOST}:{PORT}",
            f"http://localhost:{PORT}",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        }
        if origin is not None and origin not in allowed_origins:
            api_response(self, 403, {"error": "Cross-origin requests are not allowed."})
            return
        account = _authenticated_user(self)
        if account is None:
            api_response(self, 401, {"error": "Sign in to save your game."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 65536:
                raise ValueError("Save data must be between 1 and 65536 bytes.")
            body = json.loads(self.rfile.read(length))
            state = body.get("state") if isinstance(body, dict) else None
            if not isinstance(state, dict):
                raise ValueError("Save data must be a JSON object.")
            state_json = json.dumps(state, allow_nan=False, separators=(",", ":"))
            if len(state_json.encode("utf-8")) > 60000:
                raise ValueError("Save data is too large.")
        except (ValueError, json.JSONDecodeError) as error:
            api_response(self, 400, {"error": str(error)})
            return
        with connect_db() as connection:
            connection.execute(
                "INSERT INTO user_saves (user_id, state_json, updated_at) "
                "VALUES (?, ?, CURRENT_TIMESTAMP) ON CONFLICT(user_id) DO UPDATE SET "
                "state_json = excluded.state_json, updated_at = CURRENT_TIMESTAMP",
                (account[0], state_json),
            )
        api_response(self, 200, {"saved": True})

    def _sign_up(self, body: dict[str, Any]) -> None:
        username = body.get("username")
        password = body.get("password")
        if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_]{3,24}", username):
            raise ValueError("Username must be 3–24 letters, numbers, or underscores.")
        if not isinstance(password, str) or not 10 <= len(password) <= 128:
            raise ValueError("Password must be between 10 and 128 characters.")
        salt = secrets.token_bytes(16)
        try:
            with connect_db() as connection:
                cursor = connection.execute(
                    "INSERT INTO user_accounts (username, password_salt, password_hash) "
                    "VALUES (?, ?, ?)",
                    (username, salt, _password_digest(password, salt)),
                )
                user_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError as error:
            raise ValueError("That username is already taken. Try signing in.") from error
        api_response(self, 201, _issue_session(user_id, username))

    def _sign_in(self, body: dict[str, Any]) -> None:
        username = body.get("username")
        password = body.get("password")
        if not isinstance(username, str) or not isinstance(password, str) or len(password) > 128:
            raise ValueError("Enter a valid username and password.")
        with connect_db() as connection:
            account = connection.execute(
                "SELECT user_id, username, password_salt, password_hash "
                "FROM user_accounts WHERE username = ?",
                (username,),
            ).fetchone()
        salt = bytes(account["password_salt"]) if account is not None else bytes(16)
        expected = bytes(account["password_hash"]) if account is not None else bytes(32)
        actual = _password_digest(password, salt)
        if account is None or not hmac.compare_digest(actual, expected):
            api_response(self, 401, {"error": "Invalid username or password."})
            return
        api_response(self, 200, _issue_session(int(account["user_id"]), str(account["username"])))

    def _sign_out(self) -> None:
        authorization = self.headers.get("Authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and separator and len(token) <= 128:
            token_hash = hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()
            with connect_db() as connection:
                connection.execute("DELETE FROM user_sessions WHERE token_hash = ?", (token_hash,))
        api_response(self, 200, {"signed_out": True})

    def _save_run(self, body: dict[str, Any]) -> None:
        mode = body.get("mode")
        score = body.get("score")
        coins = body.get("coins")
        if mode not in VALID_MODES:
            raise ValueError("Unknown game mode.")
        if type(score) is not int or not 0 <= score <= 1_000_000:
            raise ValueError("Score must be a non-negative whole number.")
        if type(coins) is not int or not 0 <= coins <= 10_000:
            raise ValueError("Coin reward must be a non-negative whole number.")
        reference = f"PLAY-{uuid.uuid4().hex}"
        with connect_db() as connection:
            connection.execute(
                "UPDATE best_scores SET score = MAX(score, ?) WHERE mode_id = ?",
                (score, mode),
            )
            if coins:
                connection.execute(
                    "UPDATE profile SET coin_balance = coin_balance + ? WHERE id = 1",
                    (coins,),
                )
                connection.execute(
                    "INSERT INTO wallet_ledger (entry_type, coin_delta, reference_id) "
                    "VALUES ('PLAY', ?, ?)",
                    (coins, reference),
                )
            balance = connection.execute(
                "SELECT coin_balance FROM profile WHERE id = 1"
            ).fetchone()["coin_balance"]
            best = connection.execute(
                "SELECT score FROM best_scores WHERE mode_id = ?", (mode,)
            ).fetchone()["score"]
        api_response(self, 200, {"balance": balance, "best": best})

    def _new_purchase(self, body: dict[str, Any]) -> None:
        pack_id = body.get("pack_id")
        if not isinstance(pack_id, str) or len(pack_id) > 40:
            raise ValueError("Choose a valid coin pack.")
        try:
            order = create_razorpay_order(pack_id)
        except PaymentConfigurationError as error:
            api_response(self, 503, {"error": str(error)})
        except PaymentError as error:
            api_response(self, 502, {"error": str(error)})
        else:
            api_response(self, 201, order)

    def _verify_purchase(self, order_id: str, body: dict[str, Any]) -> None:
        origin = self.headers.get("Origin")
        allowed_origins = {f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"}
        if origin is not None and origin not in allowed_origins:
            api_response(self, 403, {"error": "Cross-origin requests are not allowed."})
            return
        try:
            result = verify_razorpay_payment(order_id, body)
        except ValueError as error:
            api_response(self, 400, {"error": str(error)})
        except PaymentError as error:
            api_response(self, 403, {"error": str(error)})
        else:
            api_response(self, 200, result)


class GameApp:
    WIDTH = 480
    HEIGHT = 640
    FLOOR = 34

    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Flappy Friends - Desktop")
        self.root.geometry("560x760")
        self.root.minsize(500, 480)
        self.root.configure(bg="#f2f8ff")
        self.mode_data = {mode["mode_id"]: mode for mode in self.api_get("/api/modes")["modes"]}
        self.mode_labels = {row["display_name"]: mode_id for mode_id, row in self.mode_data.items()}
        self.packs = self.api_get("/api/catalog")["packs"]
        self.mode = StringVar(value="classic")
        self.mode_name = StringVar(value=self.mode_data["classic"]["display_name"])
        self.skin = StringVar(value="Sunny")
        self.state = "intro"
        self.score = 0
        self.run_coins = 0
        self.balance = 0
        self.best = 0
        self.bird_y = 300.0
        self.bird_velocity = 0.0
        self.pipes: list[dict[str, Any]] = []
        self.coins: list[dict[str, Any]] = []
        self.particles: list[dict[str, Any]] = []
        self.stars = [(random.randrange(self.WIDTH), random.randrange(30, self.HEIGHT - 90)) for _ in range(45)]
        self.spawn_clock = 0.0
        self.last_frame = time.monotonic()
        self.elapsed = 0.0
        self.purchase_id: str | None = None
        self.purchase_url: str | None = None
        self.purchase_checking = False
        self.purchase_message = StringVar(value="Choose a coin pack to open secure Razorpay checkout.")
        self._build_ui()
        self._refresh_profile()
        self._frame()

    def api_get(self, path: str, timeout: float = 3) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(f"http://{HOST}:{PORT}{path}", timeout=timeout) as response:
                return json.loads(response.read(65536))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Local game service is unavailable: {error}") from error

    def api_post(self, path: str, data: dict[str, Any], timeout: float = 4) -> dict[str, Any]:
        body = json.dumps(data).encode("utf-8")
        request = urllib.request.Request(
            f"http://{HOST}:{PORT}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read(65536))
        except urllib.error.HTTPError as error:
            details = json.loads(error.read(8192))
            raise RuntimeError(details.get("error", f"Request failed ({error.code}).")) from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Local game service error: {error}") from error

    def _build_ui(self) -> None:
        viewport = ttk.Frame(self.root)
        viewport.pack(fill=BOTH, expand=True)
        self.scroll_canvas = Canvas(viewport, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=scrollbar.set)
        self.scroll_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        content = ttk.Frame(self.scroll_canvas)
        self.content_window = self.scroll_canvas.create_window(
            (0, 0), window=content, anchor="nw"
        )
        content.bind(
            "<Configure>",
            lambda _event: self.scroll_canvas.configure(
                scrollregion=self.scroll_canvas.bbox("all")
            ),
        )
        self.scroll_canvas.bind(
            "<Configure>",
            lambda event: self.scroll_canvas.itemconfigure(
                self.content_window, width=event.width
            ),
        )
        self.scroll_canvas.bind_all("<MouseWheel>", self._scroll_with_mouse)
        self.scroll_canvas.bind_all("<Button-4>", lambda _event: self.scroll_canvas.yview_scroll(-3, "units"))
        self.scroll_canvas.bind_all("<Button-5>", lambda _event: self.scroll_canvas.yview_scroll(3, "units"))

        heading = ttk.Frame(content, padding=(12, 12, 12, 6))
        heading.pack(fill=X)
        ttk.Label(heading, text="FLAPPY FRIENDS", font=("Segoe UI", 22, "bold")).pack()
        ttk.Label(heading, text="Pick a mode, flap through the pipes, and collect coins.").pack()

        selectors = ttk.Frame(content, padding=(12, 4))
        selectors.pack(fill=X)
        ttk.Label(selectors, text="Mode").pack(side=LEFT)
        mode_box = ttk.Combobox(
            selectors,
            textvariable=self.mode_name,
            values=list(self.mode_labels),
            state="readonly",
            width=12,
        )
        mode_box.pack(side=LEFT, padx=(6, 16))
        mode_box.bind("<<ComboboxSelected>>", self._mode_changed)
        ttk.Label(selectors, text="Skin").pack(side=LEFT)
        skin_box = ttk.Combobox(
            selectors,
            textvariable=self.skin,
            values=list(SKINS),
            state="readonly",
            width=12,
        )
        skin_box.pack(side=LEFT, padx=6)

        stats = ttk.Frame(content, padding=(12, 4))
        stats.pack(fill=X)
        self.stats_label = ttk.Label(stats, text="Score 0     Coins 0     Wallet 0     Best 0")
        self.stats_label.pack()
        self.canvas = Canvas(
            content,
            width=self.WIDTH,
            height=self.HEIGHT,
            highlightthickness=0,
            bg="#87dff2",
            cursor="hand2",
        )
        self.canvas.pack(padx=10, pady=5)
        self.canvas.bind("<Button-1>", lambda _event: self._flap())
        self.root.bind("<space>", lambda _event: self._flap())
        self.root.bind("<Up>", lambda _event: self._flap())

        shop = ttk.LabelFrame(content, text="Coin shop", padding=8)
        shop.pack(fill=X, padx=12, pady=(4, 8))
        for index, pack in enumerate(self.packs):
            price = f"₹{pack['price_paise'] / 100:g}"
            button = ttk.Button(
                shop,
                text=f"{pack['coins']} coins · {price}",
                command=lambda pack_id=pack["pack_id"]: self._buy(pack_id),
            )
            button.grid(row=index // 3, column=index % 3, sticky="ew", padx=3, pady=3)
        for column in range(3):
            shop.columnconfigure(column, weight=1)
        ttk.Label(shop, textvariable=self.purchase_message, wraplength=500).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=3, pady=(6, 0)
        )
        ttk.Label(
            content,
            text="Razorpay verifies the payment before purchased coins are added.",
            wraplength=530,
            justify=LEFT,
        ).pack(fill=X, padx=14, pady=(0, 10))

    def _scroll_with_mouse(self, event: Any) -> str:
        if event.delta:
            self.scroll_canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _refresh_profile(self) -> None:
        try:
            profile = self.api_get(f"/api/profile?mode={urllib.parse.quote(self.mode.get())}")
        except RuntimeError as error:
            self.purchase_message.set(str(error))
            return
        self.balance = profile["balance"]
        self.best = profile["best"]
        self._update_stats()

    def _update_stats(self) -> None:
        self.stats_label.configure(
            text=f"Score {self.score}     Run coins {self.run_coins}     Wallet {self.balance}     Best {self.best}"
        )

    def _mode_changed(self, _event: Any = None) -> None:
        self.mode.set(self.mode_labels[self.mode_name.get()])
        self.score = 0
        self.run_coins = 0
        if self.state == "playing":
            self.state = "ready"
        self._refresh_profile()

    def _flap(self) -> None:
        if self.state in {"intro", "ready", "over"}:
            self._start_run()
        else:
            self.bird_velocity = float(self.mode_data[self.mode.get()]["flap_strength"])

    def _start_run(self) -> None:
        self.state = "playing"
        self.score = 0
        self.run_coins = 0
        self.bird_y = self.HEIGHT * 0.47
        self.bird_velocity = float(self.mode_data[self.mode.get()]["flap_strength"])
        self.pipes.clear()
        self.coins.clear()
        self.particles.clear()
        self.spawn_clock = 0.4
        self._update_stats()

    def _add_pipe(self) -> None:
        mode = self.mode_data[self.mode.get()]
        gap = int(mode["pipe_gap"])
        low = gap / 2 + 55
        high = self.HEIGHT - self.FLOOR - gap / 2 - 55
        center = random.uniform(low, high)
        x = self.WIDTH + 20
        self.pipes.append({"x": x, "center": center, "scored": False})
        self.coins.append(
            {"x": x + 110, "y": center + random.uniform(-gap * 0.18, gap * 0.18), "collected": False}
        )

    def _end_run(self) -> None:
        if self.state != "playing":
            return
        self.state = "over"
        try:
            result = self.api_post(
                "/api/run",
                {"mode": self.mode.get(), "score": self.score, "coins": self.run_coins},
            )
            self.balance = result["balance"]
            self.best = result["best"]
        except RuntimeError as error:
            self.purchase_message.set(str(error))
        self._update_stats()

    def _buy(self, pack_id: str) -> None:
        if self.purchase_id:
            if self.purchase_url and webbrowser.open(self.purchase_url):
                self.purchase_message.set("Reopened your pending checkout. Complete it there or close it to retry later.")
            else:
                self.purchase_message.set("Could not reopen the pending checkout. Check your default browser.")
            return
        self.purchase_message.set("Creating a secure Razorpay order…")
        threading.Thread(
            target=self._create_order,
            args=(pack_id,),
            name="flappy-create-payment",
            daemon=True,
        ).start()

    def _create_order(self, pack_id: str) -> None:
        try:
            result = self.api_post("/api/purchase", {"pack_id": pack_id}, timeout=30)
        except RuntimeError as error:
            message = str(error)
            self.root.after(0, lambda: self.purchase_message.set(message))
            return
        self.root.after(0, lambda: self._open_checkout(result))

    def _open_checkout(self, result: dict[str, Any]) -> None:
        self.purchase_id = result["merchant_order_id"]
        self.purchase_url = result["checkout_url"]
        self.purchase_message.set(
            f"Opening Razorpay {result['environment']} checkout for "
            f"{result['coins']} coins (₹{result['price_paise'] / 100:g})."
        )
        if not webbrowser.open(self.purchase_url):
            self.purchase_message.set("Could not open the checkout page. Check your default browser.")
            self.purchase_id = None
            self.purchase_url = None
            return
        self.root.after(2000, self._check_purchase)

    def _check_purchase(self) -> None:
        if not self.purchase_id or self.purchase_checking:
            return
        self.purchase_checking = True
        order_id = self.purchase_id
        threading.Thread(
            target=self._fetch_purchase_status,
            args=(order_id,),
            name="flappy-check-payment",
            daemon=True,
        ).start()

    def _fetch_purchase_status(self, order_id: str) -> None:
        try:
            result = self.api_get(f"/api/purchase/{order_id}", timeout=45)
        except RuntimeError as error:
            message = str(error)
            self.root.after(0, lambda: self._purchase_check_failed(order_id, message))
            return
        self.root.after(0, lambda: self._purchase_status_received(order_id, result))

    def _purchase_check_failed(self, order_id: str, message: str) -> None:
        if self.purchase_id != order_id:
            return
        self.purchase_checking = False
        self.purchase_message.set(message)
        self.root.after(5000, self._check_purchase)

    def _purchase_status_received(self, order_id: str, result: dict[str, Any]) -> None:
        if self.purchase_id != order_id:
            return
        self.purchase_checking = False
        self.balance = result["balance"]
        self._update_stats()
        if result["state"] == "COMPLETED":
            self.purchase_message.set(f"Payment confirmed. {result['coins']} coins added.")
            self.purchase_id = None
            self.purchase_url = None
        elif result["state"] == "FAILED":
            self.purchase_message.set("Payment was not completed; no coins were added.")
            self.purchase_id = None
            self.purchase_url = None
        else:
            self.purchase_message.set("Waiting for Razorpay to confirm payment capture…")
            self.root.after(3000, self._check_purchase)

    def _draw_background(self) -> None:
        colors = SKINS[self.skin.get()]
        self.canvas.configure(bg=colors["sky"])
        self.canvas.create_rectangle(
            0, self.HEIGHT - self.FLOOR, self.WIDTH, self.HEIGHT,
            fill=colors["ground"], outline="",
        )
        self.canvas.create_rectangle(
            0, self.HEIGHT - self.FLOOR, self.WIDTH, self.HEIGHT - self.FLOOR + 7,
            fill=colors["hill"], outline="",
        )
        if self.skin.get() in {"Midnight", "Spooky"}:
            for x, y in self.stars:
                self.canvas.create_oval(x, y, x + 2, y + 2, fill="#ffffff", outline="")
        else:
            drift = int(self.elapsed * 16) % (self.WIDTH + 100)
            for base_x, y in ((55, 110), (305, 205), (205, 55)):
                x = (base_x - drift + self.WIDTH + 100) % (self.WIDTH + 100) - 40
                self.canvas.create_oval(x, y, x + 75, y + 30, fill="#ffffff", outline="")
                self.canvas.create_oval(x + 16, y - 14, x + 52, y + 24, fill="#ffffff", outline="")
        self.canvas.create_oval(-75, self.HEIGHT - 170, 190, self.HEIGHT - 53, fill=colors["hill"], outline="")
        self.canvas.create_oval(180, self.HEIGHT - 150, 560, self.HEIGHT - 47, fill=colors["hill"], outline="")

    def _draw_pipe(self, pipe: dict[str, Any]) -> None:
        colors = SKINS[self.skin.get()]
        gap = int(self.mode_data[self.mode.get()]["pipe_gap"])
        top_end = pipe["center"] - gap / 2
        bottom_start = pipe["center"] + gap / 2
        x = pipe["x"]
        for y1, y2 in ((0, top_end), (bottom_start, self.HEIGHT - self.FLOOR)):
            if y2 <= y1:
                continue
            self.canvas.create_rectangle(
                x + 5, y1, x + 67, y2, fill=colors["pipe"], outline="#253c4a", width=2
            )
            self.canvas.create_rectangle(
                x, y2 - 18 if y1 > 0 else y2 - 20, x + 72, y2 if y1 > 0 else y2 + 2,
                fill=colors["pipe"], outline="#253c4a", width=2,
            )
            if y1 == 0:
                self.canvas.create_rectangle(
                    x, y2 - 20, x + 72, y2, fill=colors["pipe"], outline="#253c4a", width=2
                )

    def _draw_bird(self) -> None:
        colors = SKINS[self.skin.get()]
        bob = math.sin(self.elapsed * 5) * 4 if self.state != "playing" else 0
        y = self.bird_y + bob
        x = 118
        self.canvas.create_polygon(
            x - 11, y + 5, x - 27, y - 2, x - 22, y + 14,
            fill=colors["pipe"], outline="#34405c", width=2,
        )
        self.canvas.create_oval(
            x - 20, y - 19, x + 20, y + 19,
            fill=colors["bird"], outline="#34405c", width=2,
        )
        self.canvas.create_oval(x + 3, y - 10, x + 16, y + 3, fill="white", outline="")
        self.canvas.create_oval(x + 10, y - 7, x + 15, y - 2, fill="#263858", outline="")
        self.canvas.create_polygon(
            x + 15, y + 1, x + 31, y + 6, x + 15, y + 11,
            fill="#f28c45", outline="#934f32",
        )
        flap = math.sin(self.elapsed * 18) * 4
        self.canvas.create_oval(
            x - 13, y + 1 + flap, x + 4, y + 12 + flap,
            fill="#fff3ba", outline="#e5a645",
        )

    def _draw_message(self) -> None:
        if self.state == "playing":
            return
        if self.state == "intro":
            title, subtitle = "FLAPPY FRIENDS", "Click or press Space to start"
        elif self.state == "ready":
            title, subtitle = "Ready to fly?", "Click or press Space to flap"
        else:
            title, subtitle = "Nice try!", f"Score {self.score}  ·  Coins {self.run_coins}  ·  Tap to retry"
        pulse = int(32 + 2 * math.sin(self.elapsed * 3))
        self.canvas.create_text(
            self.WIDTH / 2, self.HEIGHT * 0.39, text=title,
            fill="#ffffff", font=("Segoe UI", pulse, "bold"),
        )
        self.canvas.create_text(
            self.WIDTH / 2, self.HEIGHT * 0.39 + 48, text=subtitle,
            fill="#f5f8ff", font=("Segoe UI", 15, "bold"),
        )

    def _frame(self) -> None:
        now = time.monotonic()
        dt = min(now - self.last_frame, 0.04)
        self.last_frame = now
        self.elapsed += dt
        if self.state == "intro" and self.elapsed > 1.2:
            self.state = "ready"
        if self.state == "playing":
            mode = self.mode_data[self.mode.get()]
            self.bird_velocity += float(mode["gravity"]) * dt
            self.bird_y += self.bird_velocity * dt
            self.spawn_clock -= dt
            if self.spawn_clock <= 0:
                self._add_pipe()
                self.spawn_clock = float(mode["spawn_interval"])
            speed = float(mode["pipe_speed"]) + min(self.score * 2.2, 70)
            gap = int(mode["pipe_gap"])
            for pipe in self.pipes:
                pipe["x"] -= speed * dt
                if not pipe["scored"] and pipe["x"] + 72 < 118:
                    pipe["scored"] = True
                    self.score += 1
                if pipe["x"] < 153 and pipe["x"] + 72 > 83 and (
                    self.bird_y - 15 < pipe["center"] - gap / 2
                    or self.bird_y + 15 > pipe["center"] + gap / 2
                ):
                    self._end_run()
                    break
            for coin in self.coins:
                coin["x"] -= speed * dt
                if not coin["collected"] and math.hypot(118 - coin["x"], self.bird_y - coin["y"]) < 34:
                    coin["collected"] = True
                    self.run_coins += 2 if self.mode.get() == "fun" else 1
                    self.score += 2
                    for _ in range(8):
                        self.particles.append({
                            "x": coin["x"], "y": coin["y"],
                            "vx": random.uniform(-65, 65), "vy": random.uniform(-95, 30),
                            "life": 0.45,
                        })
            self.pipes = [pipe for pipe in self.pipes if pipe["x"] + 80 > 0]
            self.coins = [coin for coin in self.coins if coin["x"] > -30]
            if self.bird_y < 15 or self.bird_y > self.HEIGHT - self.FLOOR - 15:
                self._end_run()
        self._update_stats()
        self.canvas.delete("all")
        self._draw_background()
        for pipe in self.pipes:
            self._draw_pipe(pipe)
        for coin in self.coins:
            if not coin["collected"]:
                x, y = coin["x"], coin["y"]
                color = SKINS[self.skin.get()]["coin"]
                self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15, fill=color, outline="#a66c1c", width=3)
                self.canvas.create_text(x, y, text="$", fill="#fff5c3", font=("Segoe UI", 13, "bold"))
        for particle in self.particles[:]:
            particle["life"] -= dt
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            if particle["life"] <= 0:
                self.particles.remove(particle)
            else:
                self.canvas.create_oval(
                    particle["x"] - 3, particle["y"] - 3,
                    particle["x"] + 3, particle["y"] + 3,
                    fill=SKINS[self.skin.get()]["coin"], outline="",
                )
        self._draw_bird()
        self._draw_message()
        self.root.after(16, self._frame)


def run_check() -> None:
    import tempfile

    global DB_PATH
    previous_path = DB_PATH
    try:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "check.sqlite3"
            initialize_database(path)
            with connect_db() as connection:
                modes = {row[0] for row in connection.execute("SELECT mode_id FROM game_modes")}
                prices = dict(connection.execute("SELECT coins, price_paise FROM store_packs"))
                purchase_columns = {
                    row["name"] for row in connection.execute("PRAGMA table_info(purchases)")
                }
                purchase_indexes = {
                    row["name"] for row in connection.execute("PRAGMA index_list(purchases)")
                }
                account_tables = {
                    row["name"] for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' "
                        "AND name IN ('user_accounts', 'user_sessions', 'user_saves')"
                    )
                }
            expected_modes = {"classic", "chill", "speedy", "horror", "fun", "extreme"}
            expected_packs = {10: 200, 100: 1000, 200: 2000, 350: 2500, 1000: 10000, 2000: 9000}
            if (
                modes != expected_modes
                or prices != expected_packs
                or "provider_order_id" not in purchase_columns
                or "purchases_provider_order" not in purchase_indexes
                or account_tables != {"user_accounts", "user_sessions", "user_saves"}
            ):
                raise SystemExit("Database content check failed.")
    finally:
        DB_PATH = previous_path
    print("Database schema check passed: 6 modes, 6 coin packs, and persistent account saves.")


def local_service_is_ready() -> bool:
    try:
        with urllib.request.urlopen(f"http://{HOST}:{PORT}/api/health", timeout=1) as response:
            return json.loads(response.read(4096)).get("ok") is True
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False


def start_server() -> ThreadingHTTPServer:
    initialize_database()
    server = ThreadingHTTPServer((HOST, PORT), GameApiHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name="flappy-local-api", daemon=True)
    thread.start()
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Flappy Friends desktop game and local API.")
    parser.add_argument("--server-only", action="store_true", help="Run the local game and payment API without a window.")
    parser.add_argument("--check", action="store_true", help="Validate the SQL schema and seeded game content.")
    args = parser.parse_args()
    if args.check:
        run_check()
        return
    server = None if local_service_is_ready() else start_server()
    if args.server_only:
        print(f"Flappy Friends local API is available at http://{HOST}:{PORT}")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            if server is not None:
                server.shutdown()
        return
    root = Tk()
    try:
        GameApp(root)
    except (RuntimeError, sqlite3.Error) as error:
        messagebox.showerror("Flappy Friends", str(error))
        root.destroy()
        if server is not None:
            server.shutdown()
        raise
    root.mainloop()
    if server is not None:
        server.shutdown()


if __name__ == "__main__":
    main()