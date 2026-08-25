"""Seed initial data for development and testing."""
import asyncio
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Company


async def seed_companies():
    """Create sample companies if none exist."""
    async with SessionLocal() as session:
        # Check if companies already exist
        result = await session.execute(select(Company))
        existing_companies = result.scalars().all()

        if existing_companies:
            print(f"✓ {len(existing_companies)} companies already exist. Skipping seed.")
            return

        # Create sample companies
        companies = [
            Company(name="Acme Japan KK", country="Japan", entity_type="subsidiary"),
            Company(name="Acme Netherlands BV", country="Netherlands", entity_type="subsidiary"),
            Company(name="Acme Germany GmbH", country="Germany", entity_type="subsidiary"),
            Company(name="Acme UK Ltd", country="United Kingdom", entity_type="subsidiary"),
            Company(name="Acme Singapore Pte Ltd", country="Singapore", entity_type="subsidiary"),
        ]

        for company in companies:
            session.add(company)

        # Demo hierarchy: China parent entity with a Netherlands branch
        await session.flush()
        china = Company(name="Acme China Company D", country="China", entity_type="subsidiary")
        session.add(china)
        await session.flush()
        branch = Company(name="Acme Netherlands Branch", country="Netherlands", entity_type="branch", parent_entity_id=china.id)
        session.add(branch)

        await session.commit()
        print(f"✓ Created {len(companies) + 2} sample companies:")
        for company in companies + [china, branch]:
            print(f"  - {company.name} ({company.country}) [{company.entity_type}]")


async def main():
    print("🌱 Seeding database...")
    await seed_companies()
    print("✅ Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
