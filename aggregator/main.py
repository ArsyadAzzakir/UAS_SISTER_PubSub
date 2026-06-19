import os
import json
import time
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
import asyncpg
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional
from fastapi.middleware.cors import CORSMiddleware

class EventModel(BaseModel):
    topic: str
    event_id: str
    timestamp: str 
    source: str
    payload: Dict[str, Any]

db_pool = None

# Variabel global untuk mencatat statistik di memori (selama aplikasi hidup)
stats_received = 0
stats_duplicates = 0
start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    db_url = os.getenv("DATABASE_URL")
    
    retries = 5
    while retries > 0:
        try:
            db_pool = await asyncpg.create_pool(db_url)
            print("✅ Terhubung ke brankas PostgreSQL!")
            break 
        except Exception as e:
            print(f"⏳ Menunggu database siap... ({retries} percobaan tersisa). Error: {e}")
            retries -= 1
            await asyncio.sleep(3) 
            
    if not db_pool:
        print("🚨 Gagal terhubung ke database. Aplikasi akan berhenti.")
        
    yield
    
    if db_pool:
        await db_pool.close()
        print("❌ Koneksi PostgreSQL ditutup.")

app = FastAPI(title="Pub-Sub Log Aggregator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Aggregator berjalan mulus di dalam Docker!"}

@app.post("/publish")
async def publish_event(event: EventModel):
    global stats_received, stats_duplicates
    stats_received += 1  # Catat setiap request yang masuk

    query = """
        INSERT INTO processed_events (topic, event_id, timestamp, source, payload)
        VALUES ($1, $2, $3::timestamp, $4, $5::jsonb)
        ON CONFLICT (topic, event_id) DO NOTHING
        RETURNING id;
    """
    dt_obj = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00')).replace(tzinfo=None)

    async with db_pool.acquire() as connection:
        async with connection.transaction():
            result = await connection.fetchval(
                query,
                event.topic,
                event.event_id,
                dt_obj, 
                event.source,
                json.dumps(event.payload)
            )
    
    if result is None:
        stats_duplicates += 1  # Catat jika event terpantul (duplikat)
        return {"status": "ignored", "message": "Idempotent: Event duplikat, diabaikan tanpa error."}
        
    return {"status": "success", "message": "Event baru berhasil disimpan.", "inserted_id": result}

@app.get("/events")
async def get_events(topic: Optional[str] = None):
    """Melihat daftar event unik yang sudah berhasil disimpan"""
    query = "SELECT * FROM processed_events"
    args = []
    
    # Jika user mencari berdasarkan topik spesifik
    if topic:
        query += " WHERE topic = $1"
        args.append(topic)
        
    # Urutkan dari yang terbaru
    query += " ORDER BY processed_at DESC LIMIT 100"
    
    async with db_pool.acquire() as connection:
        rows = await connection.fetch(query, *args)
        
    # Format output agar mudah dibaca di Swagger/Browser
    events = []
    for row in rows:
        events.append({
            "id": row["id"],
            "topic": row["topic"],
            "event_id": row["event_id"],
            "timestamp": row["timestamp"].isoformat() + "Z",
            "source": row["source"],
            "payload": json.loads(row["payload"])
        })
        
    return {"status": "success", "total_data": len(events), "data": events}

@app.get("/stats")
async def get_stats():
    """Melihat laporan performa dan statistik sistem"""
    async with db_pool.acquire() as connection:
        # Menghitung data yang benar-benar tersimpan di database
        unique_processed = await connection.fetchval("SELECT COUNT(*) FROM processed_events")
        topics_count = await connection.fetchval("SELECT COUNT(DISTINCT topic) FROM processed_events")
    
    uptime_seconds = int(time.time() - start_time)
    
    return {
        "status": "ok",
        "uptime_seconds": uptime_seconds,
        "received": stats_received,
        "unique_processed": unique_processed,
        "duplicate_dropped": stats_duplicates,
        "topics": topics_count
    }