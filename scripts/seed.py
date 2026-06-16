import asyncio, random

from app.db.models import User
from app.db.session import async_session_maker

COUNTRIES = ["Spain", "USA", "Canada", "Russia", "France", "Japan", "Germany", "Switzerland", "Poland", "China",
             "Ukraine", "Kazakhstan", "Malaysia", "Belarus", "Iran"]


async def seed(n=100000, batch=5000):
    async with async_session_maker() as session:
        for start in range(0, n, batch):
            users = [
                User(
                    username=f"seed_{i}",
                    email=f"seed_{i}@test.com",
                    name=f"User {i}",
                    hashed_password="seed",
                    country=random.choice(COUNTRIES),
                    age=random.randint(18, 90),
                    is_verified=True,
                ) for i in range(start, start + batch)
            ]
            session.add_all(users)
            await session.commit()
            print(f"Added {start + batch} users")

asyncio.run(seed())
