#!/usr/bin/env python3
"""
n2a-account — Notion hesap ekleme CLI.

Kullanim:
    n2a-account start <email>           # mail gonder, code iste
    n2a-account verify <email> <code>   # code dogrula, hesabi ekle
    n2a-account list                   # mevcut hesaplari goster
    n2a-account activate <email>       # aktif hesap sec

Ornek (10 hesap eklemek icin):
    for i in 1..10:
      ./n2a-account start user$i@gmail.com
      echo "6-haneli kodu gir:"; read code
      ./n2a-account verify user$i@gmail.com $code
    ./n2a-account activate user1@gmail.com
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BINARY = REPO_ROOT / "bin" / "n2a-helper"
CONFIG = REPO_ROOT / "config" / "n2a-config.json"

if not BINARY.exists():
    alt = REPO_ROOT / "n2a-helper"
    if alt.exists():
        BINARY = alt
    else:
        print(f"ERROR: n2a-helper binary bulunamadi: {BINARY}", file=sys.stderr)
        print("       once 'make build' calistirin", file=sys.stderr)
        sys.exit(1)


def run(*args) -> dict:
    """helper binary'yi cagir, JSON donen komutlari parse et."""
    cmd = [str(BINARY), "--config", str(CONFIG)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    out = result.stdout.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        print(out)
        return {"_raw": out}


def start(email: str):
    out = run("start", email)
    if out.get("success"):
        print(f"✓ mail gonderildi: {email}")
        print(f"  durum: {out.get('status')}")
        print(f"  pending: {out.get('pending_state_path')}")
        print()
        print("6 haneli kodu mail'den al ve asagidaki komutu calistir:")
        print(f"  python3 {Path(__file__).name} verify {email} <KOD>")
    else:
        print(f"✗ mail gonderilemedi: {out.get('status')} — {out.get('message')}")
        sys.exit(1)


def verify(email: str, code: str):
    out = run("verify", email, code)
    if out.get("success"):
        print(f"✓ hesap eklendi: {email}")
        print(f"  user_id: {out.get('user_id')}")
        print(f"  space_id: {out.get('space_id')}")
        print(f"  probe: {out.get('probe_path')}")
        print()
        # config'e hesabi ekle (yalnizca accounts dizisine)
        activate(email)
    else:
        print(f"✗ verify basarisiz: {out.get('status')} — {out.get('message')}")
        sys.exit(1)


def activate(email: str):
    out = run("activate", email)
    print(f"✓ aktif hesap: {email}")


def list_accounts():
    out = run("accounts")
    if not out:
        print("(hesap yok)")
        return
    for i, a in enumerate(out, 1):
        print(f"  {i}. {a.get('account'):20s} email={a.get('email')} user_id={a.get('user_id')}")


def main():
    p = argparse.ArgumentParser(description="Notion hesap yonetimi")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start", help="mail gonder")
    p_start.add_argument("email")

    p_verify = sub.add_parser("verify", help="code dogrula")
    p_verify.add_argument("email")
    p_verify.add_argument("code")

    p_act = sub.add_parser("activate", help="aktif hesap sec")
    p_act.add_argument("email")

    sub.add_parser("list", help="hesaplari goster")

    args = p.parse_args()
    if args.cmd == "start":
        start(args.email)
    elif args.cmd == "verify":
        verify(args.email, args.code)
    elif args.cmd == "activate":
        activate(args.email)
    elif args.cmd == "list":
        list_accounts()


if __name__ == "__main__":
    main()
