from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    servers = relationship("Server", back_populates="owner")


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    host = Column(String, index=True)
    port = Column(Integer, default=25565)
    nickname = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="servers")
    polls = relationship("PollResult", back_populates="server")


class PollResult(Base):
    __tablename__ = "poll_results"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"))
    online = Column(Boolean)
    player_count = Column(Integer, nullable=True)
    max_players = Column(Integer, nullable=True)
    motd = Column(String, nullable=True)
    version = Column(String, nullable=True)
    latency = Column(Integer, nullable=True)
    polled_at = Column(DateTime, default=datetime.utcnow)

    server = relationship("Server", back_populates="polls")
