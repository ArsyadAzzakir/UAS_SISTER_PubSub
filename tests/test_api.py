import pytest
import httpx
import uuid

# Kita menembak langsung ke container Aggregator yang sedang berjalan
BASE_URL = "http://host.docker.internal:8080"

def generate_payload(event_id):
    return {
        "topic": "pytest_topic",
        "event_id": event_id,
        "timestamp": "2026-06-16T12:00:00Z",
        "source": "pytest-script",
        "payload": {"suhu": 22.5, "status": "testing"}
    }

def test_api_root_is_online():
    """Memastikan layanan utama hidup"""
    r = httpx.get(f"{BASE_URL}/")
    assert r.status_code == 200

def test_api_stats_accessible():
    """Memastikan endpoint metrik bisa diakses"""
    r = httpx.get(f"{BASE_URL}/stats")
    assert r.status_code == 200
    assert "unique_processed" in r.json()

def test_api_events_accessible():
    """Memastikan log data bisa diakses"""
    r = httpx.get(f"{BASE_URL}/events")
    assert r.status_code == 200

def test_publish_new_valid_event():
    """Memastikan event baru bisa disimpan dengan sukses"""
    event_id = f"test-new-{uuid.uuid4()}"
    r = httpx.post(f"{BASE_URL}/publish", json=generate_payload(event_id))
    assert r.status_code == 200
    assert r.json()["status"] == "success"

def test_publish_duplicate_idempotency():
    """Memastikan event duplikat ditolak secara atomik (Idempotent)"""
    event_id = f"test-dup-{uuid.uuid4()}"
    payload = generate_payload(event_id)
    
    # Tembakan 1: Harus sukses
    r1 = httpx.post(f"{BASE_URL}/publish", json=payload)
    assert r1.status_code == 200
    assert r1.json()["status"] == "success"
    
    # Tembakan 2: Harus ignored (ditangkis)
    r2 = httpx.post(f"{BASE_URL}/publish", json=payload)
    assert r2.status_code == 200
    assert r2.json()["status"] == "ignored"

# Menggunakan parameterisasi untuk langsung membuat 10 skenario tes paralel otomatis
@pytest.mark.parametrize("execution_number", range(1, 11))
def test_bulk_insert_consistency(execution_number):
    """Skenario berulang: Memastikan konsistensi input data dalam jumlah banyak"""
    event_id = f"test-bulk-{execution_number}-{uuid.uuid4()}"
    r = httpx.post(f"{BASE_URL}/publish", json=generate_payload(event_id))
    assert r.status_code == 200
    assert r.json()["status"] == "success"