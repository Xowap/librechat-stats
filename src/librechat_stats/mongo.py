from dataclasses import dataclass, field
from datetime import datetime

import pymongo

from .models import Conversation, Message, Transaction, User


def guess_domain(email: str | None) -> str:
    if email and "@" in email:
        return email.split("@")[1]

    return "<unknown>"


@dataclass
class LibreChatMongo:
    dsn: str
    db: str = field(init=False)
    client: pymongo.MongoClient = field(init=False)

    def __post_init__(self):
        self.client = pymongo.MongoClient(self.dsn)
        self.db = self.client.get_default_database().name

    def get_collection(self, name: str, since: datetime) -> list[dict]:
        return list(self.client[self.db][name].find({"createdAt": {"$gte": since}}))

    def get_messages(self, since: datetime) -> list[Message]:
        return [
            Message(
                id=str(message["_id"]),
                user_id=message["user"],
                conversation_id=message["conversationId"],
                date=message["createdAt"],
                sender="user" if message["isCreatedByUser"] else "llm",
                endpoint=message.get("endpoint", "") or "",
                model=message.get("model", "") or "",
            )
            for message in self.get_collection("messages", since)
        ]

    def get_transactions(self, since: datetime) -> list[Transaction]:
        return [
            Transaction(
                id=str(transaction["_id"]),
                user_id=str(transaction["user"]),
                conversation_id=transaction.get("conversationId", "") or "",
                context=transaction["context"],
                date=transaction["createdAt"],
                model=transaction["model"],
                pricing_type=transaction["tokenType"],
                token_count=transaction["rawAmount"] * -1,
                usd_per_million=transaction["rate"],
                usd_total=transaction["tokenValue"] / -1_000_000.0,
            )
            for transaction in self.get_collection("transactions", since)
        ]

    def get_conversations(self, since: datetime) -> list[Conversation]:
        return [
            Conversation(
                id=str(conversation["_id"]),
                user_id=conversation["user"],
                date=conversation["createdAt"],
                endpoint=conversation["endpoint"],
                model=conversation["model"],
            )
            for conversation in self.get_collection("conversations", since)
        ]

    def get_users(self, since: datetime) -> list[User]:
        return [
            User(
                id=str(user["_id"]),
                created_at=user["createdAt"],
                domain=guess_domain(user.get("email")),
            )
            for user in self.get_collection("users", since)
        ]
