from __future__ import annotations
import time
from sqlmodel import Field, SQLModel, create_engine

class PhotoBatch(SQLModel, table=True):
    __tablename__ = "photo_batches"
    id: int | None = Field(default=None, primary_key=True)
    queue_item_id: int
    venue_id: int
    perf_date: str
    status: str = Field(default="staging")
    created_at: float = Field(default_factory=time.time)

class PhotoAsset(SQLModel, table=True):
    __tablename__ = "photo_assets"
    id: int | None = Field(default=None, primary_key=True)
    batch_id: int = Field(foreign_key="photo_batches.id")
    kind: str  # 'slip' or 'stage'
    file_path: str
    sha256: str
    uploaded_at: float = Field(default_factory=time.time)

class PhotoAssetEntry(SQLModel, table=True):
    __tablename__ = "photo_asset_entries"
    id: int | None = Field(default=None, primary_key=True)
    photo_asset_id: int = Field(foreign_key="photo_assets.id")
    participant_entry_id: int
    source: str  # 'stagemaster_quick' or 'data_worker'
    assigned_at: float = Field(default_factory=time.time)

def init_db(db_url: str):
    engine = create_engine(db_url)
    SQLModel.metadata.create_all(engine)
    return engine
