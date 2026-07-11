from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr

class UserOut(BaseModel):
    email: str
    api_key: str
    created_at: datetime

    class Config:
        from_attributes = True

class ServerCreate(BaseModel):
    host: str
    port: int = 25565
    nickname: Optional[str] = None

class ServerOut(BaseModel):
    id: int
    host: str
    port: int
    nickname: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class PollResultOut(BaseModel):
    id: int
    online: bool
    player_count: Optional[int]
    max_players: Optional[int]
    motd: Optional[str]
    version: Optional[str]
    latency: Optional[int]
    polled_at: datetime

    class Config:
        from_attributes = True

class ServerStats(BaseModel):
    server_id: int
    host: str
    total_polls: int
    uptime_percent: float
    peak_players: Optional[int]
    average_players: Optional[float]

class PaginatedPolls(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[PollResultOut]