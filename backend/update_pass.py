import asyncio
from core.database import db

async def update():
    await db.get_pool()
    await db.execute("UPDATE users SET password_hash = '$2b$12$Fzb/GpHPGjxnsa24xwR2feuXagsC8bfX/hCHsFeLQtxZrfaDeYlbu' WHERE email = 'admin@evidra.gov'")
    print("Updated password to admin123")

if __name__ == "__main__":
    asyncio.run(update())
