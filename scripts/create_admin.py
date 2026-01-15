import asyncio
import sys
from sqlalchemy import select

from appp.database import AsyncSessionLocal
from appp.core.security import hash_password
from appp import models


async def create_admins(pairs: list[tuple[str, str]]):
    async with AsyncSessionLocal() as db:
        for username, password in pairs:
            result = await db.execute(
                select(models.Admin).where(models.Admin.username == username)
            )
            admin = result.scalar_one_or_none()

            if admin:
                print(f"Admin '{username}' existe déjà, ignoré")
                continue

            new_admin = models.Admin(
                username=username,
                password_hash=hash_password(password),
                is_active=True
            )

            db.add(new_admin)
            await db.commit()
            print(f"Admin '{username}' créé")

    print("Terminé")


def parse_args():
    args = sys.argv[1:]

    if len(args) == 0 or len(args) % 2 != 0:
        print(
            "Usage:\n"
            "python scripts/create_admin.py <username1> <password1> [<username2> <password2> ...]"
        )
        sys.exit(1)

    return [(args[i], args[i + 1]) for i in range(0, len(args), 2)]


if __name__ == "__main__":
    pairs = parse_args()
    asyncio.run(create_admins(pairs))
