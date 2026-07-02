import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base

class Month(Base):
    __tablename__ = "months"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False)
    title = Column(String, nullable=False)
    focus = Column(String, nullable=True)
    build_target = Column(String, nullable=True)

    weeks = relationship("Week", back_populates="month", cascade="all, delete-orphan")

class Week(Base):
    __tablename__ = "weeks"

    id = Column(Integer, primary_key=True, index=True)
    month_id = Column(Integer, ForeignKey("months.id", ondelete="CASCADE"), nullable=False)
    number = Column(Integer, unique=True, nullable=False)
    title = Column(String, nullable=False)

    month = relationship("Month", back_populates="weeks")
    topics = relationship("Topic", back_populates="week", cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    week_id = Column(Integer, ForeignKey("weeks.id", ondelete="CASCADE"), nullable=False)
    content = Column(String, nullable=False)
    category = Column(String, nullable=False)  # 'learn' or 'build'
    order_num = Column(Integer, nullable=False)

    week = relationship("Week", back_populates="topics")
    progress = relationship("UserProgress", back_populates="topic", uselist=False, cascade="all, delete-orphan")

class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), unique=True, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    topic = relationship("Topic", back_populates="progress")

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    current_topic_id = Column(Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    last_active_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    current_topic = relationship("Topic")
