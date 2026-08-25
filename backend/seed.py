"""Seed initial data for development and testing."""
import asyncio
from sqlalchemy import select
from app.database import async_session_maker
from app.models import Company


async def seed_companies():
    """Create sample companies if none exist."""
    async with async_session_maker() as session:
        # Check if companies already exist
        result = await session.execute(select(Company))
        existing_companies = result.scalars().all()

        if existing_companies:
            print(f"✓ {len(existing_companies)} companies already exist. Skipping seed.")
            return

        # Create sample companies
        companies = [
            Company(name="Acme Japan KK", country="Japan"),
            Company(name="Acme Netherlands BV", country="Netherlands"),
            Company(name="Acme Germany GmbH", country="Germany"),
            Company(name="Acme UK Ltd", country="United Kingdom"),
            Company(name="Acme Singapore Pte Ltd", country="Singapore"),
        ]

        for company in companies:
            session.add(company)

        await session.commit()
        print(f"✓ Created {len(companies)} sample companies:")
        for company in companies:
            print(f"  - {company.name} ({company.country})")


async def main():
    print("🌱 Seeding database...")
    await seed_companies()
    print("✅ Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
