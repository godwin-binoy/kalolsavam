from __future__ import annotations
import time
from sqlmodel import Field, SQLModel, create_engine

class LogEntry(SQLModel, table=True):
    __tablename__ = "log_entries"
    id: int | None = Field(default=None, primary_key=True)
    ts: float = Field(default_factory=time.time)
    service: str
    level: str
    msg: str
    request_id: str | None = None
    method: str | None = None
    path: str | None = None
    status: int | None = None
    duration_ms: int | None = None
    client_ip: str | None = None

def init_db(db_url: str):
    engine = create_engine(db_url)
    SQLModel.metadata.create_all(engine)
    return engine
