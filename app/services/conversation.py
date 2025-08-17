from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from db.models.conversation import Conversation
from uuid import UUID

async def get_conversation_with_turns(db: AsyncSession, photo_id: UUID, conversation_id: UUID):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.turns))
        .where(
            Conversation.id == conversation_id,
            Conversation.photo_id == photo_id
        )
    )
    conversation = result.scalars().first()
    return conversation

async def get_latest_conversation_for_photo(db: AsyncSession, photo_id: UUID):
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.turns))
        .where(Conversation.photo_id == photo_id)
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    conversation = result.scalars().first()
    return conversation

async def get_conversation_origin_text(db: AsyncSession, conversation_id: UUID):
    from db.models.turn import Turn
    result = await db.execute(
        select(Turn).where(Turn.conv_id == conversation_id).order_by(Turn.recorded_at)
    )
    turns = result.scalars().all()
    origin_text = []
    for turn in turns:
        if turn.turn:
            origin_text.append({
                "q_text": turn.turn.get("q_text"),
                "a_text": turn.turn.get("a_text")
            })
    return origin_text

async def get_conversation_origin_voice(db: AsyncSession, conversation_id: UUID):
    from db.models.turn import Turn
    result = await db.execute(
        select(Turn).where(Turn.conv_id == conversation_id).order_by(Turn.recorded_at)
    )
    turns = result.scalars().all()
    origin_voice = []
    for turn in turns:
        if turn.turn:
            origin_voice.append({
                "q_voice": turn.turn.get("q_voice"),
                "a_voice": turn.turn.get("a_voice")
            })
    return origin_voice 