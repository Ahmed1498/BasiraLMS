from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Message, User

router = APIRouter(prefix="/api/v1", tags=["Messages"])


class MessageCreate(BaseModel):
    recipient_id: UUID
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)


@router.get("/messages")
async def list_messages(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Message)
        .where(or_(Message.sender_id == user.id, Message.recipient_id == user.id))
        .order_by(Message.sent_at.desc())
    )
    messages = result.scalars().all()
    user_ids = {message.sender_id for message in messages} | {message.recipient_id for message in messages}
    people_result = await db.execute(select(User).where(User.id.in_(user_ids))) if user_ids else None
    people = {person.id: person for person in people_result.scalars().all()} if people_result else {}

    return {
        "messages": [
            {
                "id": str(message.id),
                "sender_id": str(message.sender_id),
                "recipient_id": str(message.recipient_id),
                "sender_name": people.get(message.sender_id).full_name if people.get(message.sender_id) else "Unknown",
                "recipient_name": people.get(message.recipient_id).full_name if people.get(message.recipient_id) else "Unknown",
                "subject": message.subject,
                "body": message.body,
                "sent_at": message.sent_at.isoformat() if message.sent_at else None,
                "is_read": message.is_read,
                "direction": "sent" if message.sender_id == user.id else "received",
            }
            for message in messages
        ]
    }


@router.post("/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    recipient = await db.get(User, data.recipient_id)
    if recipient is None:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if not recipient.is_active:
        raise HTTPException(status_code=400, detail="Recipient account is inactive")

    message = Message(
        sender_id=user.id,
        recipient_id=data.recipient_id,
        subject=data.subject,
        body=data.body,
    )
    db.add(message)
    await db.flush()
    return {"id": str(message.id), "subject": message.subject}


@router.post("/messages/{message_id}/read")
async def mark_message_read(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    message = await db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.recipient_id != user.id:
        raise HTTPException(status_code=403, detail="You can only mark messages addressed to you as read")
    message.is_read = True
    await db.flush()
    return {"id": str(message.id), "is_read": True}


@router.get("/users/contacts")
async def list_contacts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(User)
        .where(User.is_active.is_(True), User.id != user.id)
        .order_by(User.full_name)
    )
    return {
        "users": [
            {"id": str(contact.id), "full_name": contact.full_name, "email": contact.email, "role": contact.role}
            for contact in result.scalars().all()
        ]
    }
