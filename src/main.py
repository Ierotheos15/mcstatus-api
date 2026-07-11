from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from src.database import get_db, engine, SessionLocal
from src import models, schemas, auth
from src.poller import poll_server, poll_server_async
from src.auth import generate_api_key, get_current_user
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio

models.Base.metadata.create_all(bind=engine)

async def background_poller():
    while True:
        await asyncio.sleep(300)
        db = SessionLocal()
        try:
            servers = db.query(models.Server).all()
            for server in servers:
                await poll_server_async(server.host, server.port, server.id, db)
        finally:
            db.close()

@asynccontextmanager
async def lifespan(app):
    asyncio.create_task(background_poller())
    yield

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    lifespan=lifespan,
    title="mcstatus-api",
    description="UptimeRobot for Minecraft servers. Track uptime, player counts, and history.",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- Auth ---

@app.post("/register", response_model=schemas.UserOut, tags=["Auth"])
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = models.User(
        email=user.email,
        api_key=generate_api_key()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# --- Servers ---

@app.post("/servers", response_model=schemas.ServerOut, tags=["Servers"])
@limiter.limit("20/minute")
def add_server(request: Request, server: schemas.ServerCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    existing = db.query(models.Server).filter(
        models.Server.host == server.host,
        models.Server.port == server.port,
        models.Server.owner_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Server already registered")
    new_server = models.Server(
        host=server.host,
        port=server.port,
        nickname=server.nickname,
        owner_id=current_user.id
    )
    db.add(new_server)
    db.commit()
    db.refresh(new_server)
    return new_server

@app.get("/servers", response_model=list[schemas.ServerOut], tags=["Servers"])
@limiter.limit("30/minute")
def list_servers(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Server).filter(models.Server.owner_id == current_user.id).all()

@app.delete("/servers/{server_id}", tags=["Servers"])
@limiter.limit("10/minute")
def delete_server(request: Request, server_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    server = db.query(models.Server).filter(
        models.Server.id == server_id,
        models.Server.owner_id == current_user.id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    db.delete(server)
    db.commit()
    return {"detail": "Server deleted"}


# --- Polling ---

@app.post("/servers/{server_id}/poll", response_model=schemas.PollResultOut, tags=["Polling"])
@limiter.limit("5/minute")
async def manual_poll(request: Request, server_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    server = db.query(models.Server).filter(
        models.Server.id == server_id,
        models.Server.owner_id == current_user.id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return await poll_server_async(server.host, server.port, server.id, db)

@app.get("/servers/{server_id}/history", response_model=schemas.PaginatedPolls, tags=["Polling"])
@limiter.limit("30/minute")
def poll_history(
    request: Request,
    server_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    server = db.query(models.Server).filter(
        models.Server.id == server_id,
        models.Server.owner_id == current_user.id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    total = db.query(models.PollResult).filter(models.PollResult.server_id == server_id).count()
    results = (
        db.query(models.PollResult)
        .filter(models.PollResult.server_id == server_id)
        .order_by(models.PollResult.polled_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return schemas.PaginatedPolls(total=total, page=page, page_size=page_size, results=results)


# --- Stats ---

@app.get("/servers/{server_id}/stats", response_model=schemas.ServerStats, tags=["Stats"])
@limiter.limit("30/minute")
def server_stats(request: Request, server_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    server = db.query(models.Server).filter(
        models.Server.id == server_id,
        models.Server.owner_id == current_user.id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    polls = db.query(models.PollResult).filter(models.PollResult.server_id == server_id).all()
    if not polls:
        raise HTTPException(status_code=404, detail="No poll data yet")

    total = len(polls)
    online_polls = [p for p in polls if p.online]
    uptime = round(len(online_polls) / total * 100, 2)
    player_counts = [p.player_count for p in online_polls if p.player_count is not None]
    peak = max(player_counts) if player_counts else None
    average = round(sum(player_counts) / len(player_counts), 2) if player_counts else None

    return schemas.ServerStats(
        server_id=server.id,
        host=server.host,
        total_polls=total,
        uptime_percent=uptime,
        peak_players=peak,
        average_players=average
    )


# --- Quick lookup (no auth) ---

@app.get("/lookup", tags=["Public"])
@limiter.limit("10/minute")
async def quick_lookup(request: Request, host: str, port: int = 25565):
    from mcstatus import JavaServer
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        def do_lookup():
            server = JavaServer.lookup(f"{host}:{port}", timeout=10)
            return server.status()
        status = await loop.run_in_executor(None, do_lookup)
        return {
            "online": True,
            "host": host,
            "port": port,
            "players": status.players.online,
            "max_players": status.players.max,
            "motd": str(status.description),
            "version": status.version.name,
            "latency_ms": int(status.latency)
        }
    except Exception as e:
        return {
            "online": False,
            "host": host,
            "port": port,
            "error": str(e)
        }