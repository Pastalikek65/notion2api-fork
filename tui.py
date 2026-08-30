#!/usr/bin/env python3
import asyncio, json, os, signal, subprocess, sys, time, urllib.parse
from pathlib import Path

import requests
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Header, Footer, Input, Label, RichLog, Static, TabbedContent, TabPane

BASE = Path(__file__).parent.resolve()
BIN = BASE / "bin"
CONFIG_FILE = BASE / "config" / "n2a-config.json"
PIDFILE = BASE / ".server.pid"


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


# ── Admin API Client ──────────────────────────────────────────────

class AdminClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.s = requests.Session()

    def login(self, password: str) -> bool:
        try:
            r = self.s.post(f"{self.base_url}/admin/login", json={"password": password}, timeout=5)
            return r.ok
        except Exception:
            return False

    def get_accounts(self) -> tuple:
        try:
            r = self.s.get(f"{self.base_url}/admin/accounts", timeout=5)
            if r.ok:
                d = r.json()
                return d.get("items", []), d.get("active_account", "")
            return [], ""
        except Exception:
            return [], ""

    def account_login_start(self, email: str) -> dict:
        try:
            r = self.s.post(f"{self.base_url}/admin/accounts/login/start", json={"email": email}, timeout=10)
            if r.ok:
                return {"ok": True}
            return {"ok": False, "error": _clean_err(r.text)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def account_login_verify(self, email: str, code: str) -> dict:
        try:
            r = self.s.post(f"{self.base_url}/admin/accounts/login/verify", json={"email": email, "code": code}, timeout=30)
            if r.ok:
                return {"ok": True}
            return {"ok": False, "error": _clean_err(r.text)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def account_delete(self, email: str) -> dict:
        try:
            r = self.s.delete(f"{self.base_url}/admin/accounts/{urllib.parse.quote(email)}", timeout=5)
            return {"ok": r.ok, "error": _clean_err(r.text)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def account_activate(self, email: str) -> dict:
        try:
            r = self.s.post(f"{self.base_url}/admin/accounts/activate", json={"email": email}, timeout=5)
            return {"ok": r.ok, "error": _clean_err(r.text)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def account_test(self, email: str, model: str = "haiku-4.5") -> dict:
        try:
            r = self.s.post(
                f"{self.base_url}/admin/accounts/test",
                json={"email": email, "model": model, "prompt": "Reply with NOTION2API_ACCOUNT_OK only."},
                timeout=60,
            )
            if r.ok:
                d = r.json()
                return {"ok": True, "result": d.get("result", d.get("text", "ok"))[:300]}
            return {"ok": False, "error": _clean_err(r.text)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_healthz(self) -> dict:
        try:
            r = self.s.get(f"{self.base_url}/healthz", timeout=5)
            return r.json() if r.ok else {}
        except Exception:
            return {}

    def get_models(self) -> list:
        try:
            cfg = load_config()
            api_key = cfg.get("api_key", "")
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            r = self.s.get(f"{self.base_url}/v1/models", headers=headers, timeout=5)
            if r.ok:
                return r.json().get("data", [])
            return []
        except Exception:
            return []


def _clean_err(text: str) -> str:
    try:
        d = json.loads(text)
        if isinstance(d, dict):
            return str(d.get("detail") or d.get("message") or text)[:200]
    except Exception:
        pass
    return text[:200]


# ── Dialogs ───────────────────────────────────────────────────────

class InputDialog(ModalScreen):
    def __init__(self, title: str, label: str, placeholder: str = "", secret: bool = False):
        super().__init__()
        self._title = title
        self._label = label
        self._placeholder = placeholder
        self._secret = secret

    def compose(self):
        with Vertical(id="dialog-box"):
            yield Label(f"[bold]{self._title}[/]", id="dialog-title")
            yield Label(self._label, id="dialog-label")
            yield Input(placeholder=self._placeholder, password=self._secret, id="dialog-input")
            with Horizontal(id="dialog-buttons"):
                yield Button("OK", variant="primary", id="dialog-ok")
                yield Button("Cancel", variant="default", id="dialog-cancel")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "dialog-ok":
            self.dismiss(self.query_one("#dialog-input", Input).value.strip() or None)
        else:
            self.dismiss(None)

    def on_mount(self):
        self.query_one("#dialog-input", Input).focus()


class ConfirmDialog(ModalScreen):
    def __init__(self, title: str, message: str):
        super().__init__()
        self._title = title
        self._message = message

    def compose(self):
        with Vertical(id="dialog-box"):
            yield Label(f"[bold]{self._title}[/]", id="dialog-title")
            yield Label(self._message, id="dialog-label")
            with Horizontal(id="dialog-buttons"):
                yield Button("Yes", variant="error", id="dialog-yes")
                yield Button("No", variant="primary", id="dialog-no")

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(event.button.id == "dialog-yes")


# ── Server action worker helper ───────────────────────────────────

def run_server_action(action: str, log=None) -> bool:
    def w(msg):
        if log:
            log.write(msg)
    if action == "start":
        if get_server_pid():
            w("Already running.")
            time.sleep(0.5)
            return True
        w("Starting server...")
        ok = start_server_process()
        w("Server started." if ok else "Failed to start.")
        time.sleep(1.5)
        return ok
    if action == "stop":
        if not get_server_pid():
            w("Not running.")
            time.sleep(0.5)
            return True
        w(f"Stopping PID {get_server_pid()}...")
        ok = stop_server_process()
        w("Stopped." if ok else "Failed to stop.")
        time.sleep(0.5)
        return ok
    if action == "restart":
        w("Restarting...")
        stop_server_process()
        time.sleep(1)
        ok = start_server_process()
        w("Restarted." if ok else "Failed to restart.")
        time.sleep(1.5)
        return ok
    return False


# ── Main App ──────────────────────────────────────────────────────

class Notion2APITUI(App):
    TITLE = "Notion2API Manager"

    CSS = """
    #dialog-box {
        width: 55;
        height: auto;
        padding: 1 2;
        border: thick $primary;
        background: $surface;
        margin: 2 8;
    }
    #dialog-title { text-style: bold; margin-bottom: 1; }
    #dialog-label { margin-bottom: 1; }
    #dialog-input { margin-bottom: 1; }
    #dialog-buttons { height: 3; align: center middle; }
    #dialog-buttons Button { margin: 0 1; }

    TabPane { padding: 1; }
    .card { border: solid $primary-lighten-2; padding: 1 2; margin: 1 0; }
    .card-title { text-style: bold; }

    #login-box { width: 44; height: auto; padding: 1 2; border: thick $primary; background: $surface; }
    #login-box Input { margin-bottom: 1; }
    #login-box Button { width: 100%; }

    #dash-grid Horizontal { height: auto; }
    .dash-card { border: solid $primary-lighten-2; padding: 1 2; margin: 1; width: 1fr; }
    .dash-card Label { margin: 0; }

    #actions-bar { height: 5; align: center middle; }
    #actions-bar Button { margin: 0 1; min-width: 14; }

    #accounts-table { height: 1fr; }
    #add-account-form { height: auto; border: solid $primary-lighten-2; padding: 1; margin: 1 0; }
    #account-detail { height: auto; min-height: 3; border: solid $primary-lighten-2; padding: 1; margin: 1 0; }
    #models-table { height: 1fr; }
    #models-detail { height: auto; min-height: 3; border: solid $primary-lighten-2; padding: 1; margin: 1 0; }
    #server-info { min-height: 6; }

    #status-bar { height: 3; padding: 0 1; background: $panel; border-bottom: solid $primary; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "go_dashboard", "Dashboard"),
        Binding("a", "go_accounts", "Accounts"),
        Binding("s", "go_server", "Server"),
        Binding("m", "go_models", "Models"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self):
        super().__init__()
        cfg = load_config()
        port = cfg.get("port", 8787)
        self.admin = AdminClient(f"http://127.0.0.1:{port}")
        self.authenticated = False
        self._auto_refresh_task = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="status-bar")
        with TabbedContent(initial="dashboard"):
            with TabPane("Dashboard", id="dashboard"):
                yield DashboardScreen()
            with TabPane("Accounts", id="accounts"):
                yield AccountsScreen()
            with TabPane("Server", id="server"):
                yield ServerScreen()
            with TabPane("Models", id="models"):
                yield ModelsScreen()
        yield Footer()

    def on_mount(self):
        self.push_screen(LoginScreen(self.admin), self._on_login)

    def _on_login(self, ok: bool):
        if not ok:
            self.exit("Login failed")
            return
        self.authenticated = True
        self.notify("Logged in", timeout=3)
        self.refresh_all()
        self._start_auto_refresh()

    def _start_auto_refresh(self):
        async def loop():
            try:
                while True:
                    await asyncio.sleep(5)
                    self.call_from_thread(self._safe_refresh)
            except asyncio.CancelledError:
                pass
        self._auto_refresh_task = asyncio.ensure_future(loop())

    def on_unmount(self):
        if self._auto_refresh_task:
            self._auto_refresh_task.cancel()

    def _safe_refresh(self):
        try:
            self.refresh_all()
        except Exception:
            pass

    def refresh_all(self):
        for w in self.query(DashboardScreen):
            w.refresh_data(self.admin)
        for w in self.query(AccountsScreen):
            w.refresh_data(self.admin)
        for w in self.query(ServerScreen):
            w.refresh_data(self.admin)
        for w in self.query(ModelsScreen):
            w.refresh_data(self.admin)

    def _update_status_bar(self):
        sb = self.query_one("#status-bar", Static)
        hz = self.admin.get_healthz()
        ok = hz.get("ok", False)
        pid = get_server_pid()
        running = "🟢 Running" if ok else "🔴 Stopped"
        sb.update(f" {running}   PID {pid or '-'}   Active: {hz.get('active_account', '-')}   Models: {hz.get('model_count', '?')}   [dim](R refresh / Q quit)[/]")

    def action_go_dashboard(self): self.query_one(TabbedContent).active = "dashboard"
    def action_go_accounts(self): self.query_one(TabbedContent).active = "accounts"
    def action_go_server(self): self.query_one(TabbedContent).active = "server"
    def action_go_models(self): self.query_one(TabbedContent).active = "models"

    def action_refresh(self):
        self.refresh_all()
        self._update_status_bar()


# ── Login Screen ─────────────────────────────────────────────────

class LoginScreen(Screen):
    def __init__(self, admin: AdminClient):
        super().__init__()
        self.admin = admin

    def compose(self):
        with Vertical(id="login-box", classes="center"):
            yield Label("[bold cyan]Notion2API Manager[/]", id="dialog-title")
            yield Label(f"Server: {self.admin.base_url}")
            yield Input(placeholder="Admin password", password=True, id="login-password")
            yield Button("Login", variant="primary", id="login-btn")

    def on_mount(self):
        self.query_one("#login-password", Input).focus()

    def on_button_pressed(self, event: Button.Pressed):
        pw = self.query_one("#login-password", Input).value
        if self.admin.login(pw):
            self.dismiss(True)
        else:
            self.notify("Wrong password or server down", severity="error", timeout=3)
            self.query_one("#login-password", Input).value = ""
            self.query_one("#login-password", Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        pw = self.query_one("#login-password", Input).value
        if self.admin.login(pw):
            self.dismiss(True)
        else:
            self.notify("Wrong password or server down", severity="error", timeout=3)
            self.query_one("#login-password", Input).value = ""
            self.query_one("#login-password", Input).focus()


# ── Dashboard ────────────────────────────────────────────────────

class DashboardScreen(ScrollableContainer):
    def compose(self):
        with Vertical(id="dash-grid"):
            with Horizontal():
                yield Static(id="dash-server", classes="dash-card")
                yield Static(id="dash-active", classes="dash-card")
            with Horizontal():
                yield Static(id="dash-accounts-summary", classes="dash-card")
                yield Static(id="dash-quick", classes="dash-card")
            yield Static(id="dash-accounts", classes="card")
            with Horizontal(id="actions-bar"):
                yield Button("▶ Start", variant="success", id="dash-start")
                yield Button("⏹ Stop", variant="error", id="dash-stop")
                yield Button("🔄 Restart", variant="warning", id="dash-restart")
                yield Button("➕ Add Account", variant="primary", id="dash-add")

    def refresh_data(self, admin: AdminClient):
        if admin is None:
            return
        hz = admin.get_healthz()
        accounts, active = admin.get_accounts()
        ok = hz.get("ok", False)
        pid = get_server_pid()

        self.query_one("#dash-server", Static).update(
            f"[bold]Server[/]\n"
            f"Status: {'🟢 Running' if ok else '🔴 Stopped'}\n"
            f"PID: {pid or '-'}\n"
            f"Models: {hz.get('model_count', '?')}\n"
            f"Session: {'✅ ready' if hz.get('session_ready') else '❌ not ready'}"
        )

        act = next((a for a in accounts if a.get("active")), None)
        self.query_one("#dash-active", Static).update(
            f"[bold]Active Account[/]\n"
            f"Email: {act.get('email', '-') if act else '-'}\n"
            f"Status: {act.get('status', '-') if act else '-'}\n"
            f"Space: {act.get('space_name', '-') if act else '-'}\n"
            f"Last Err: {str(act.get('last_error', '-'))[:50] if act else '-'}"
        )

        n_ready = sum(1 for a in accounts if a.get("status") == "ready")
        self.query_one("#dash-accounts-summary", Static).update(
            f"[bold]Accounts[/]\n"
            f"Total: {len(accounts)}\n"
            f"Ready: {n_ready}\n"
            f"Active: {active or '-'}"
        )

        self.query_one("#dash-quick", Static).update(
            f"[bold]Quick Info[/]\n"
            f"Refresh: {str(hz.get('last_session_refresh', '-'))[:19]}\n"
            f"Refresh Err: {str(hz.get('last_session_refresh_error', ''))[:40] or 'none'}\n"
            f"Default Model: {hz.get('default_model', 'auto')}"
        )

        if accounts:
            lines = ["[bold]Accounts[/]"]
            for a in accounts:
                s = a.get("status", "?")
                icon = "🟢" if s == "ready" else "🟡" if "pending" in s or "login" in s else "🔴"
                mark = " (active)" if a.get("active") else ""
                lines.append(f"  {icon} {a.get('email','?')} — {s}{mark}")
            self.query_one("#dash-accounts", Static).update("\n".join(lines))
        else:
            self.query_one("#dash-accounts", Static).update("[bold]Accounts[/]\n  (none)")

        self.query_one("#dash-start", Button).disabled = ok
        self.query_one("#dash-stop", Button).disabled = not ok
        self.query_one("#dash-restart", Button).disabled = not ok

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "dash-start":
            self.app.push_screen(ServerActionDialog("start"))
        elif bid == "dash-stop":
            self.app.push_screen(ServerActionDialog("stop"))
        elif bid == "dash-restart":
            self.app.push_screen(ServerActionDialog("restart"))
        elif bid == "dash-add":
            self._add_account()

    def _add_account(self):
        def on_email(email: str):
            if not email or "@" not in email:
                self.app.notify("Valid email required", severity="error")
                return
            result = self.app.admin.account_login_start(email)
            if not result.get("ok"):
                self.app.notify(f"❌ {result.get('error','?')}", severity="error", timeout=6)
                return
            self.app.notify(f"Code sent to {email}. Enter it below.", timeout=6)
            def on_code(code: str):
                if not code:
                    return
                self.app.notify("Verifying...", timeout=10)
                res = self.app.admin.account_login_verify(email, code)
                if res.get("ok"):
                    self.app.notify(f"✅ {email} added & activated", timeout=5)
                    self.app.refresh_all()
                else:
                    self.app.notify(f"❌ {res.get('error','?')}", severity="error", timeout=8)
            self.app.push_screen(InputDialog("Verify Code", f"6-digit code for {email}:", placeholder="000000"), on_code)
        self.app.push_screen(InputDialog("Add Account", "Email address:", placeholder="user@example.com"), on_email)


# ── Accounts ─────────────────────────────────────────────────────

class AccountsScreen(ScrollableContainer):
    def compose(self):
        with Vertical():
            yield DataTable(id="accounts-table")
            with Horizontal(id="add-account-form"):
                yield Input(placeholder="Email to add...", id="add-email")
                yield Button("➕ Add", variant="primary", id="btn-add")
            with Horizontal():
                yield Button("🔌 Activate", variant="warning", id="btn-activate")
                yield Button("🧪 Test", variant="success", id="btn-test")
                yield Button("🗑 Remove", variant="error", id="btn-remove")
                yield Button("🔄 Refresh", variant="default", id="btn-refresh")
            yield Static(id="account-detail")

    def on_mount(self):
        table = self.query_one("#accounts-table", DataTable)
        table.add_columns("Email", "Status", "User", "Space", "Failures", "Active")
        table.cursor_type = "row"
        self.refresh_data(None)

    def refresh_data(self, admin: AdminClient):
        if admin is None:
            return
        accounts, _ = admin.get_accounts()
        table = self.query_one("#accounts-table", DataTable)
        table.clear()
        for a in accounts:
            table.add_row(
                a.get("email", "?"),
                a.get("status", "?"),
                str(a.get("user_name", ""))[:20],
                str(a.get("space_name", ""))[:20],
                str(a.get("consecutive_failures", 0)),
                "✅" if a.get("active") else "",
            )

    def _selected_email(self) -> str:
        table = self.query_one("#accounts-table", DataTable)
        if table.row_count == 0:
            return ""
        row = table.get_row_at(table.cursor_row)
        return row[0] if row else ""

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "btn-add":
            inp = self.query_one("#add-email", Input)
            addr = inp.value.strip()
            if not addr or "@" not in addr:
                self.app.notify("Valid email required", severity="error")
                return
            result = self.app.admin.account_login_start(addr)
            if not result.get("ok"):
                self.app.notify(f"❌ {result.get('error','?')}", severity="error", timeout=6)
                return
            def on_code(code: str):
                if not code:
                    return
                res = self.app.admin.account_login_verify(addr, code)
                if res.get("ok"):
                    self.app.notify(f"✅ {addr} added", timeout=5)
                    inp.value = ""
                    self.app.refresh_all()
                else:
                    self.app.notify(f"❌ {res.get('error','?')}", severity="error", timeout=8)
            self.app.push_screen(InputDialog("Verify Code", f"6-digit code for {addr}:", placeholder="000000"), on_code)
        elif bid == "btn-activate":
            email = self._selected_email()
            if not email:
                self.app.notify("Select an account first", severity="warning")
                return
            res = self.app.admin.account_activate(email)
            if res.get("ok"):
                self.app.notify(f"✅ {email} activated", timeout=3)
                self.app.refresh_all()
            else:
                self.app.notify(f"❌ {res.get('error','?')}", severity="error", timeout=6)
        elif bid == "btn-test":
            email = self._selected_email()
            if not email:
                self.app.notify("Select an account first", severity="warning")
                return
            self.app.notify(f"Testing {email}...", timeout=15)
            res = self.app.admin.account_test(email)
            detail = self.query_one("#account-detail", Static)
            if res.get("ok"):
                detail.update(f"[bold]Test {email}[/]\n✅ {res.get('result','')}")
            else:
                detail.update(f"[bold]Test {email}[/]\n❌ {res.get('error','?')}")
        elif bid == "btn-remove":
            email = self._selected_email()
            if not email:
                self.app.notify("Select an account first", severity="warning")
                return
            def on_confirm(yes: bool):
                if not yes:
                    return
                res = self.app.admin.account_delete(email)
                if res.get("ok"):
                    self.app.notify(f"🗑 {email} removed", timeout=3)
                    self.app.refresh_all()
                else:
                    self.app.notify(f"❌ {res.get('error','?')}", severity="error", timeout=6)
            self.app.push_screen(ConfirmDialog("Remove Account", f"Remove {email}?"), on_confirm)
        elif bid == "btn-refresh":
            self.app.refresh_all()
            self.app.notify("Refreshed", timeout=2)


# ── Server ───────────────────────────────────────────────────────

class ServerScreen(ScrollableContainer):
    def compose(self):
        with Vertical():
            yield Static(id="server-info", classes="card")
            with Horizontal():
                yield Button("▶ Start", variant="success", id="srv-start")
                yield Button("⏹ Stop", variant="error", id="srv-stop")
                yield Button("🔄 Restart", variant="warning", id="srv-restart")
            yield Static(id="server-log", classes="card")

    def refresh_data(self, admin: AdminClient):
        if admin is None:
            return
        hz = admin.get_healthz()
        ok = hz.get("ok", False)
        self.query_one("#server-info", Static).update(
            f"[bold]Server Status[/]\n"
            f"OK: {'✅' if ok else '❌'}\n"
            f"Models: {hz.get('model_count', '?')}\n"
            f"Default Model: {hz.get('default_model', 'auto')}\n"
            f"Active Account: {hz.get('active_account', '-')}\n"
            f"Session Ready: {'✅' if hz.get('session_ready') else '❌'}\n"
            f"Last Refresh: {str(hz.get('last_session_refresh', '-'))[:19]}\n"
            f"Refresh Error: {str(hz.get('last_session_refresh_error', ''))[:60] or 'none'}"
        )
        self.query_one("#srv-start", Button).disabled = ok
        self.query_one("#srv-stop", Button).disabled = not ok
        self.query_one("#srv-restart", Button).disabled = not ok

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "srv-start":
            self.app.push_screen(ServerActionDialog("start"))
        elif bid == "srv-stop":
            self.app.push_screen(ServerActionDialog("stop"))
        elif bid == "srv-restart":
            self.app.push_screen(ServerActionDialog("restart"))


# ── Models ───────────────────────────────────────────────────────

class ModelsScreen(ScrollableContainer):
    def compose(self):
        with Vertical():
            yield DataTable(id="models-table")
            with Horizontal():
                yield Button("🔄 Refresh", variant="default", id="models-refresh")
                yield Button("🧪 Test", variant="success", id="models-test")
            yield Static(id="models-detail")

    def on_mount(self):
        table = self.query_one("#models-table", DataTable)
        table.add_columns("ID", "Name", "Family", "Beta")
        table.cursor_type = "row"
        self.refresh_data(None)

    def refresh_data(self, admin: AdminClient):
        if admin is None:
            return
        models = admin.get_models()
        table = self.query_one("#models-table", DataTable)
        table.clear()
        for m in models:
            table.add_row(
                m.get("id", "?"),
                m.get("name", m.get("id", "?")),
                m.get("family", "-"),
                "⚠" if m.get("beta") else "",
            )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "models-refresh":
            self.app.refresh_all()
            self.app.notify("Refreshed", timeout=2)
        elif event.button.id == "models-test":
            table = self.query_one("#models-table", DataTable)
            if table.row_count == 0:
                return
            row = table.get_row_at(table.cursor_row)
            model_id = row[0]
            self.app.notify(f"Testing {model_id}...", timeout=15)
            res = self.app.admin.account_test("", model_id)
            detail = self.query_one("#models-detail", Static)
            if res.get("ok"):
                detail.update(f"[bold]Test {model_id}[/]\n✅ {res.get('result','')}")
            else:
                detail.update(f"[bold]Test {model_id}[/]\n❌ {res.get('error','?')}")


# ── Server Action Dialog ─────────────────────────────────────────

class ServerActionDialog(ModalScreen):
    def __init__(self, action: str):
        super().__init__()
        self.action = action

    def compose(self):
        with Vertical(id="dialog-box"):
            yield Label(f"[bold]Server {self.action}...[/]", id="dialog-title")
            yield RichLog(id="dialog-log", highlight=True, wrap=True, max_lines=30)

    def on_mount(self):
        self.run_worker(self._run, thread=True)

    def _run(self):
        log = self.query_one("#dialog-log", RichLog)
        ok = run_server_action(self.action, log)
        time.sleep(0.3)
        self.call_from_thread(self.dismiss, ok)


# ── Server helpers ───────────────────────────────────────────────

def get_server_pid():
    if PIDFILE.exists():
        try:
            pid = int(PIDFILE.read_text().strip())
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError, ProcessLookupError):
            PIDFILE.unlink(missing_ok=True)
    return None

def start_server_process():
    bin_path = BIN / "notion2api"
    if not bin_path.exists():
        return False
    try:
        proc = subprocess.Popen(
            [str(bin_path), "--config", str(CONFIG_FILE)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        PIDFILE.write_text(str(proc.pid))
        return True
    except Exception:
        return False

def stop_server_process():
    pid = get_server_pid()
    if not pid:
        return True
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(12):
            try:
                os.kill(pid, 0)
                time.sleep(0.3)
            except (OSError, ProcessLookupError):
                break
        else:
            os.kill(pid, signal.SIGKILL)
        PIDFILE.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def main():
    Notion2APITUI().run()


if __name__ == "__main__":
    main()