# mcstatus-api

A REST API for monitoring Minecraft server uptime, player counts, and history. Think UptimeRobot, but for Minecraft servers.

## Features

- Track any Java Edition Minecraft server
- Automatic polling every 5 minutes
- Historical player count and uptime stats
- Public lookup endpoint (no auth required)
- API key authentication
- Rate limiting

## Base URL

https://ierotheos.site

## Authentication

Register to get an API key:

```http
POST /register
Content-Type: application/json

{
  "email": "you@example.com"
}
```

Use the returned `api_key` as the `x-api-key` header in all authenticated requests.

**Demo key:** `1_5SYTbRZQjfVkvg8QQ7yd918-3gtAT5QPXIjjf9J-E`

## Endpoints

### Public

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/lookup?host=mc.example.com&port=25565` | Quick one-off server status, no auth |
| GET | `/docs` | Interactive API documentation |

### Authenticated

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register and get an API key |
| POST | `/servers` | Register a server to monitor |
| GET | `/servers` | List your monitored servers |
| DELETE | `/servers/{id}` | Remove a server |
| POST | `/servers/{id}/poll` | Manually trigger a poll |
| GET | `/servers/{id}/history` | Paginated poll history |
| GET | `/servers/{id}/stats` | Uptime %, peak and average players |

## Example Requests

**Quick lookup:**
```http
GET /lookup?host=play.cubecraft.net
```

**Add a server:**
```http
POST /servers
x-api-key: YOUR_API_KEY
Content-Type: application/json

{
  "host": "play.cubecraft.net",
  "port": 25565,
  "nickname": "CubeCraft"
}
```

**Get history (paginated):**
```http
GET /servers/1/history?page=1&page_size=20
x-api-key: YOUR_API_KEY
```

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/lookup` | 10/minute |
| `/servers/{id}/poll` | 5/minute |
| `/servers` (POST) | 20/minute |
| Most GET endpoints | 30/minute |

## Stack

- Python + FastAPI
- SQLite + SQLAlchemy
- mcstatus library for Minecraft protocol
- slowapi for rate limiting
