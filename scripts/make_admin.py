#!/usr/bin/env python3
"""Grant or revoke the admin role for an existing account (run on the server, next to the database).

    python scripts/make_admin.py --email you@example.com
    python scripts/make_admin.py --username ryantruong --revoke
    python scripts/make_admin.py --list
"""
import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import func  # noqa: E402

from server.database import SessionLocal, init_db  # noqa: E402
from server.models import User  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Grant or revoke the TOEIC Lab admin role.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--email")
    target.add_argument("--username")
    target.add_argument("--list", action="store_true", help="List current admins")
    parser.add_argument("--revoke", action="store_true", help="Set the role back to learner")
    args = parser.parse_args(argv)

    init_db()
    with SessionLocal() as db:
        if args.list:
            for user in db.query(User).filter(User.role == "admin").order_by(User.id):
                print(f"#{user.id} {user.username} <{user.email}> active={user.is_active is not False}")
            return 0

        column, value = (User.email, args.email) if args.email else (User.username, args.username)
        user = db.query(User).filter(func.lower(column) == value.strip().lower()).first()
        if user is None:
            print(f"No account found for {value!r}. Register it on the website first.", file=sys.stderr)
            return 1
        if not user.hashed_password:
            print(f"Account {user.username!r} has no password; it cannot sign in, so it cannot be an admin.", file=sys.stderr)
            return 1

        user.role = "learner" if args.revoke else "admin"
        if not args.revoke:
            user.is_active = True
        db.commit()
        print(f"#{user.id} {user.username} -> role={user.role}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
