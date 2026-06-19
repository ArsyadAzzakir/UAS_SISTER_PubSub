import os
import json
import time
import random
import asyncio
import httpx
from datetime import datetime, timezone

TARGET_URL = os.getenv("TARGET_URL", "http://aggregator:8080/publish")
TOPICS = ["sensor_suhu", "sensor_kelembapan", "sensor_cahaya"]
SOURCES = ["device-01", "device-02", "device-03"]

async def send_event(client: httpx.AsyncClient, event_data: dict):
    """Menembakkan satu event ke Aggregator"""
    try:
        response = await client.post(TARGET_URL, json=event_data)
        return response.status_code
    except Exception as e:
        print(f"Error mengirim event: {e}")
        return None

async def main():
    print(f"🚀 Publisher mulai! Target: {TARGET_URL}")
    
    # Tunggu sebentar agar Aggregator benar-benar siap
    await asyncio.sleep(5)
    
    # Menyimpan daftar ID yang sudah dibuat agar bisa disimulasikan sebagai duplikat
    history_ids = []
    
    async with httpx.AsyncClient() as client:
        for i in range(1, 1001): # Kita tembakkan 1000 data dulu untuk tes awal
            
            # Simulasi peluang 30% untuk mengirim data duplikat (sesuai spesifikasi soal)
            is_duplicate = random.random() < 0.3 and len(history_ids) > 0
            
            if is_duplicate:
                # Ambil ID lama yang sudah pernah dikirim
                event_id = random.choice(history_ids)
                topic = "sensor_suhu" # Topiknya kita samakan agar memicu conflict
                print(f"⚠️ Mengirim Ulang Duplikat: {event_id}")
            else:
                # Buat ID baru
                event_id = f"evt-auto-{i}-{int(time.time() * 1000)}"
                topic = random.choice(TOPICS)
                history_ids.append(event_id)
            
            # Merakit payload JSON
            event = {
                "topic": topic,
                "event_id": event_id,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "source": random.choice(SOURCES),
                "payload": {
                    "value": round(random.uniform(20.0, 80.0), 2),
                    "status": "active"
                }
            }
            
            # Tembak!
            await send_event(client, event)
            
            # Delay sedikit agar log terminal tidak terlalu kacau
            await asyncio.sleep(0.05) 
            
    print("✅ Publisher selesai menembakkan 1000 event simulasi.")
    # Biarkan container tetap hidup agar Docker tidak merestartnya terus menerus
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())