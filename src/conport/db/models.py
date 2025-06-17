import datetime
from typing import Any
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base, DeclarativeBase

# Define the Base HERE, within the models.py file.
Base: type[DeclarativeBase] = declarative_base()

# Core Data Models
class ProductContext(Base):
    __tablename__ = "product_context"
    id = Column(Integer, primary_key=True, default=1)
    content = Column(JSON, nullable=False, default={})

class ActiveContext(Base):
    __tablename__ = "active_context"
    id = Column(Integer, primary_key=True, default=1)
    content = Column(JSON, nullable=False, default={})

class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    summary = Column(String, nullable=False, index=True)
    rationale = Column(Text, nullable=True)
    implementation_details = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)

class ProgressEntry(Base):
    __tablename__ = "progress_entries"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    status = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey("progress_entries.id", ondelete="SET NULL"), nullable=True)
    parent = relationship("ProgressEntry", remote_side=[id], back_populates="children")
    children = relationship("ProgressEntry", back_populates="parent", cascade="all, delete-orphan", lazy="joined")

class SystemPattern(Base):
    __tablename__ = "system_patterns"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)

class CustomData(Base):
    __tablename__ = "custom_data"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    category = Column(String, index=True, nullable=False)
    key = Column(String, index=True, nullable=False)
    value = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint('category', 'key', name='_category_key_uc'),)

# Knowledge Graph Model
class ContextLink(Base):
    __tablename__ = "context_links"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    source_item_type = Column(String, nullable=False, index=True)
    source_item_id = Column(String, nullable=False, index=True)
    target_item_type = Column(String, nullable=False, index=True)
    target_item_id = Column(String, nullable=False, index=True)
    relationship_type = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)

# History/Audit Models
class ProductContextHistory(Base):
    __tablename__ = "product_context_history"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    version = Column(Integer, nullable=False)
    content = Column(JSON, nullable=False)
    change_source = Column(String, nullable=True)

class ActiveContextHistory(Base):
    __tablename__ = "active_context_history"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    version = Column(Integer, nullable=False)
    content = Column(JSON, nullable=False)
    change_source = Column(String, nullable=True)