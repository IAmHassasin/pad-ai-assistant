"""Batch: Gemini parse desc_en → active/leader_skill_effects (chạy một lần / bổ sung dần)."""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import Config
from database.sqlite_client import SQLiteClient
from services.skill_effect_parser import SkillEffectParser


def run_batch(
    side: str,
    limit: int,
    delay_sec: float,
    dry_run: bool,
    order: str,
) -> None:
    Config.validate(require_gemini=True)
    client = SQLiteClient(Config.SQLITE_DB_PATH)
    store = client.custom_effects
    parser = SkillEffectParser()
    pending = store.skills_missing_effects(side, limit=limit, order=order)
    order_label = "cao → thấp" if order == "desc" else "thấp → cao"
    print(
        f"📋 {side}: {len(pending)} skills chưa có custom effects "
        f"(limit={limit}, id {order_label})"
    )
    if pending:
        ids = [row[f"{side}_skill_id"] for row in pending]
        print(f"   ID batch: #{max(ids)} … #{min(ids)}")

    for i, row in enumerate(pending, 1):
        skill_id = row[f"{side}_skill_id"]
        desc = row.get("desc_en") or ""
        if not desc.strip():
            continue
        try:
            effects = parser.parse_skill_description(side, skill_id, desc)
        except Exception as e:
            print(f"  [{i}] #{skill_id} SKIP parse error: {e}")
            continue

        print(f"  [{i}] #{skill_id} {row.get('name_en', '')[:40]} → {len(effects)} effects")
        for eff in effects:
            key = eff.get("effect_key") or eff.get("key_name")
            if not key:
                continue
            print(f"       - {key} v1={eff.get('value_1')} turns={eff.get('turn_duration')}")
            if not dry_run:
                store.set_skill_effect(
                    side,
                    skill_id,
                    key,
                    value_1=eff.get("value_1"),
                    value_2=eff.get("value_2"),
                    turn_duration=eff.get("turn_duration"),
                    source="gemini",
                )
        if delay_sec > 0 and not dry_run:
            time.sleep(delay_sec)

    client.close()
    print("✅ Done." if not dry_run else "✅ Dry run complete.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=("leader", "active"), required=True)
    ap.add_argument("--limit", type=int, default=100, help="Max skills per run")
    ap.add_argument(
        "--order",
        choices=("desc", "asc"),
        default="desc",
        help="Thứ tự active_skill_id: desc = từ lớn xuống nhỏ (mặc định)",
    )
    ap.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    run_batch(args.side, args.limit, args.delay, args.dry_run, args.order)


if __name__ == "__main__":
    main()
