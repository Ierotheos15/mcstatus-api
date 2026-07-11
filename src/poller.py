from mcstatus import JavaServer
from sqlalchemy.orm import Session
from src import models
from datetime import datetime
import asyncio

def poll_server(host: str, port: int, server_id: int, db: Session) -> models.PollResult:
    result = models.PollResult(
        server_id=server_id,
        polled_at=datetime.utcnow()
    )

    try:
        server = JavaServer.lookup(f"{host}:{port}", timeout=10)
        status = server.status()

        result.online = True
        result.player_count = status.players.online
        result.max_players = status.players.max
        result.motd = str(status.description)
        result.version = status.version.name
        result.latency = int(status.latency)

    except Exception as e:
        result.online = False
        result.player_count = None
        result.max_players = None
        result.motd = None
        result.version = None
        result.latency = None

    db.add(result)
    db.commit()
    db.refresh(result)
    return result

async def poll_server_async(host: str, port: int, server_id: int, db: Session) -> models.PollResult:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, poll_server, host, port, server_id, db)