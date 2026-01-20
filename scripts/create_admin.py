import asyncio
import sys
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app import models


"""
ATTENTION : Pour des raisons de sécurité, évitez de passer les mots de passe en ligne de commande en production.
Préférez l'utilisation de variables d'environnement ou d'un prompt interactif pour saisir les mots de passe.
"""
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
                hashed_password=get_password_hash(password),
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
