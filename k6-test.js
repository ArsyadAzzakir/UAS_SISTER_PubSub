import http from 'k6/http';
import { check } from 'k6';

export const options = {
    vus: 50, // 50 virtual users menembak berbarengan secara paralel
    iterations: 20000, // Total target 20.000 request sesuai tugas
};

export default function () {
    // Kita gunakan host.docker.internal agar container K6 bisa menembus masuk ke localhost Windows-mu
    const url = 'http://host.docker.internal:8080/publish';
    
    // Membuat simulasi duplikat: Setiap kelipatan 5, kita pakai ID yang sengaja disamakan
    const isDuplicate = __ITER % 5 === 0;
    const eventId = isDuplicate ? `evt-k6-duplicate-${__ITER % 100}` : `evt-k6-unik-${__VU}-${__ITER}`;
    
    const payload = JSON.stringify({
        topic: "sensor_stress_test",
        event_id: eventId,
        timestamp: new Date().toISOString(),
        source: "k6-load-tester",
        payload: {
            tekanan: Math.random() * 100,
            status: "testing"
        }
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const res = http.post(url, payload, params);
    
    // Mengecek apakah server berhasil merespons tanpa error 500
    check(res, {
        'status is 200 (Success/Ignored)': (r) => r.status === 200,
    });
}