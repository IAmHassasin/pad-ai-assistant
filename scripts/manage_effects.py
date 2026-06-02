"""CLI quản lý effect_types bổ sung và gán vào skill."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import Config
from database.sqlite_client import SQLiteClient


def cmd_list(args: argparse.Namespace) -> None:
    client = SQLiteClient(Config.SQLITE_DB_PATH)
    store = client.custom_effects
    for side in ("leader", "active"):
        if args.side and args.side != side:
            continue
        types = store.list_effect_types(side)
        print(f"\n=== {side}_effect_types ({len(types)}) ===")
        for row in types:
            print(f"  {row['effect_type_id']:4} {row['key_name']:24} {row['display_name']}")
    client.close()


def cmd_add_type(args: argparse.Namespace) -> None:
    client = SQLiteClient(Config.SQLITE_DB_PATH)
    eid = client.custom_effects.upsert_effect_type(
        args.side,
        args.key,
        args.display or args.key.replace("_", " ").title(),
        args.description,
    )
    print(f"✅ {args.side} effect type #{eid} key={args.key!r}")
    client.close()


def cmd_set_skill(args: argparse.Namespace) -> None:
    client = SQLiteClient(Config.SQLITE_DB_PATH)
    store = client.custom_effects
    store.set_skill_effect(
        args.side,
        args.skill_id,
        args.key,
        value_1=args.value1,
        value_2=args.value2,
        turn_duration=args.turns,
        source=args.source,
        notes=args.notes,
    )
    print(f"✅ Gán {args.key!r} → {args.side}_skill_id={args.skill_id}")
    client.close()


def cmd_show_skill(args: argparse.Namespace) -> None:
    client = SQLiteClient(Config.SQLITE_DB_PATH)
    rows = client.custom_effects.list_skill_effects(args.side, args.skill_id)
    print(f"\n{args.side} skill #{args.skill_id} — {len(rows)} custom effects:")
    for r in rows:
        print(
            f"  {r['key_name']}: v1={r['value_1']} v2={r['value_2']} "
            f"turns={r['turn_duration']} ({r['source']})"
        )
    client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage PAD custom effect types")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List effect types")
    p_list.add_argument("--side", choices=("leader", "active"))
    p_list.set_defaults(func=cmd_list)

    p_add = sub.add_parser("add-type", help="Add or update effect type")
    p_add.add_argument("side", choices=("leader", "active"))
    p_add.add_argument("key", help="snake_case key_name")
    p_add.add_argument("--display", help="Human-readable name")
    p_add.add_argument("--description")
    p_add.set_defaults(func=cmd_add_type)

    p_set = sub.add_parser("set-skill", help="Assign effect to a skill id")
    p_set.add_argument("side", choices=("leader", "active"))
    p_set.add_argument("skill_id", type=int)
    p_set.add_argument("key")
    p_set.add_argument("--value1", type=float)
    p_set.add_argument("--value2", type=float)
    p_set.add_argument("--turns", type=int)
    p_set.add_argument("--source", default="manual")
    p_set.add_argument("--notes")
    p_set.set_defaults(func=cmd_set_skill)

    p_show = sub.add_parser("show-skill", help="List effects on one skill")
    p_show.add_argument("side", choices=("leader", "active"))
    p_show.add_argument("skill_id", type=int)
    p_show.set_defaults(func=cmd_show_skill)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
