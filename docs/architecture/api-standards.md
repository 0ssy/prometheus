# API Standards

## Base URL

```
http://127.0.0.1:8000
```

## Conventions

- All endpoints return JSON.
- Errors use FastAPI's `HTTPException` with appropriate status codes.
- Successful writes return the created resource or confirmation.
- All mutating endpoints record a knowledge-graph fact via `assert_fact()`.

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created (not currently used) |
| 400 | Bad request — invalid parameters |
| 403 | Forbidden — ownership not declared or OS denied access |
| 404 | Not found — device, file, or disk path missing |
| 500 | Internal server error |

## Endpoint Groups

### Health
- `GET /health` — Service health and loaded modules.

### Memory
- `POST /memory` — Store a memory entry.
- `GET /memory` — Recall memory entries, optionally filtered by tag.

### Knowledge Graph
- `POST /knowledge` — Assert a new fact.
- `GET /knowledge` — Query facts, optionally filtered by subject.

### Devices
- `POST /devices/simulated` — Register a simulated device.
- `POST /devices/serial` — Register a serial device.
- `GET /devices` — List all registered devices.
- `GET /devices/{device_id}` — Get device status.
- `POST /devices/{device_id}/write` — Write to a device.
- `POST /devices/{device_id}/disconnect` — Disconnect a device.

### Ownership
- `POST /ownership/declare` — Declare ownership of a target.
- `GET /ownership` — List declared ownerships.
- `DELETE /ownership/{target_id:path}` — Revoke ownership declaration.

### Gamma — Firmware & Boot
- `GET /gamma/partitions` — Read partition table (requires declared ownership).
- `GET /gamma/firmware` — Inspect firmware image (requires declared ownership).
- `GET /gamma/simulate/{scenario}` — Run Boot Chain + Recovery pipeline on simulated device.

### Delta — Digital Twin
- `GET /delta/twin/{device_id}` — Get the materialized digital twin.

### Epsilon — Autonomous Engineering
- `POST /epsilon/plan` — Create an engineering plan.
- `GET /epsilon/suggestions` — Get improvement suggestions.
- `GET /epsilon/backlog` — Get the capability backlog.

## Versioning

API versioning is not yet implemented. Endpoints may change until v1.0.
