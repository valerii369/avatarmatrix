import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.core.economy import award_energy, process_referral_reward, spend_energy

@pytest.mark.asyncio
async def test_referral_flow(db_session: AsyncSession):
    # 1. Create Referrer
    referrer = User(tg_id=111, first_name="Referrer", energy=500, referral_code="REF123")
    db_session.add(referrer)
    await db_session.commit()
    await db_session.refresh(referrer)

    # 2. Create Joiner
    joiner = User(tg_id=222, first_name="Joiner", energy=500, referred_by=referrer.id)
    db_session.add(joiner)
    await db_session.commit()
    await db_session.refresh(joiner)

    # 3. Process Rewards
    await process_referral_reward(db_session, joiner)
    await db_session.commit()
    await db_session.refresh(joiner)
    await db_session.refresh(referrer)

    # Joiner should have 500 (initial) + 500 (bonus) = 1000
    assert joiner.energy == 1000
    # Referrer should have 500 (initial) + 200 (bonus) = 700
    assert referrer.energy == 700

@pytest.mark.asyncio
async def test_spend_energy_insufficient(db_session: AsyncSession):
    user = User(tg_id=333, energy=10)
    db_session.add(user)
    await db_session.commit()

    # Sync costs 35
    success = await spend_energy(db_session, user, "sync")
    assert success is False
    assert user.energy == 10
