from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# ---------------------------------------------------------------------------
# SQLAlchemy declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class UserTable(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # operator | curator
    created_at = Column(DateTime, server_default=func.now())

    collections = relationship("CollectionTable", back_populates="owner")


class CollectionTable(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    dollar_goal = Column(Float, nullable=True)  # V2 killer feature
    created_at = Column(DateTime, server_default=func.now())

    owner = relationship("UserTable", back_populates="collections")
    items = relationship("ItemTable", back_populates="collection")


class ItemTable(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False, index=True)
    brand = Column(String(255), default="unknown")
    description = Column(Text, default="")
    condition_score = Column(Float, nullable=True)
    status = Column(String(20), default="undecided")  # undecided | keeper | seller
    created_at = Column(DateTime, server_default=func.now())

    collection = relationship("CollectionTable", back_populates="items")
    photos = relationship("ItemPhotoTable", back_populates="item")


class ItemPhotoTable(Base):
    __tablename__ = "item_photos"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    storage_key = Column(String(500), nullable=False)
    is_hero = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    item = relationship("ItemTable", back_populates="photos")


class SessionTable(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)


class UsedTokenTable(Base):
    __tablename__ = "used_tokens"
    id = Column(Integer, primary_key=True)
    jti = Column(String(255), unique=True, nullable=False, index=True)
    used_at = Column(DateTime, server_default=func.now())


class ComparisonTable(Base):
    __tablename__ = "comparisons"

    id = Column(Integer, primary_key=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_a_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    item_b_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    winner_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    info_level_shown = Column(String(20), nullable=False)  # photos_only | brand | condition | price
    created_at = Column(DateTime, server_default=func.now())


class EloRatingTable(Base):
    __tablename__ = "elo_ratings"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rating = Column(Float, default=1500.0)
    comparison_count = Column(Integer, default=0)


class PriceEstimateTable(Base):
    __tablename__ = "price_estimates"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    source = Column(String(100), nullable=False)
    estimated_value = Column(Float, nullable=True)
    comps_data = Column(Text, nullable=True)  # JSON blob
    fetched_at = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Pydantic schemas (frozen — API layer)
# ---------------------------------------------------------------------------

VALID_ROLES = ("operator", "curator")
VALID_STATUSES = ("undecided", "keeper", "seller")
VALID_INFO_LEVELS = ("photos_only", "brand", "condition", "price")


class UserCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str
    name: str
    role: Literal["operator", "curator"]


class UserRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    email: str
    name: str
    role: str
    created_at: Optional[datetime] = None


class CollectionCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str = ""
    dollar_goal: Optional[float] = None


class CollectionRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    owner_id: int
    name: str
    description: str
    dollar_goal: Optional[float] = None
    created_at: Optional[datetime] = None


class ItemCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    collection_id: int
    brand: str = "unknown"
    description: str = ""
    condition_score: Optional[float] = None
    status: Literal["undecided", "keeper", "seller"] = "undecided"


class ItemRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    collection_id: int
    brand: str
    description: str
    condition_score: Optional[float] = None
    status: str
    created_at: Optional[datetime] = None


class ItemPhotoRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    item_id: int
    storage_key: str
    is_hero: bool
    sort_order: int


class ComparisonCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    collection_id: int
    user_id: int
    item_a_id: int
    item_b_id: int
    winner_id: int
    info_level_shown: Literal["photos_only", "brand", "condition", "price"]


class ComparisonRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    collection_id: int
    user_id: int
    item_a_id: int
    item_b_id: int
    winner_id: int
    info_level_shown: str
    created_at: Optional[datetime] = None


class EloRatingRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    item_id: int
    collection_id: int
    user_id: int
    rating: float
    comparison_count: int


class PriceEstimateRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    item_id: int
    source: str
    estimated_value: Optional[float] = None
    comps_data: Optional[str] = None
    fetched_at: Optional[datetime] = None
