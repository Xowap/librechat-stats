from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(kw_only=True)
class Message:
    id: str
    user_id: str
    conversation_id: str
    date: datetime
    sender: Literal["user", "llm"]
    endpoint: str
    model: str


@dataclass(kw_only=True)
class Transaction:
    id: str
    user_id: str
    conversation_id: str
    context: Literal["message", "title"]
    date: datetime
    model: str
    pricing_type: Literal["completion", "prompt"]
    token_count: int
    usd_per_million: float
    usd_total: float


@dataclass(kw_only=True)
class Conversation:
    id: str
    user_id: str
    date: datetime
    endpoint: str
    model: str


@dataclass(kw_only=True)
class User:
    id: str
    created_at: datetime
    domain: str
