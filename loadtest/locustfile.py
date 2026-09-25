"""Locust-Lasttest fuer Rudis Reifenklicker.

Beispiele:
    LOCUST_HOST=http://localhost:8080 locust -f locustfile.py
    LOCUST_HOST=http://localhost:8080 locust -f locustfile.py --headless -u 50 -r 5 -t 3m

Der Test sammelt zusaetzlich, welche Backend-Version die Klicks
beantwortet hat. Damit laesst sich der Canary-Traffic-Anteil
(Sommer- vs. Winterreifen) in Zahlen beobachten.
"""

import threading
from collections import Counter

from locust import HttpUser, between, events, task

VERSION_COUNTS: Counter = Counter()
_lock = threading.Lock()


class ReifenklickerUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.client.get("/api/count", name="/api/count")

    @task(1)
    def click(self):
        with self.client.post("/api/click", name="/api/click", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return
            response.success()
            try:
                version = response.json().get("version", "unbekannt")
            except ValueError:
                return
            with _lock:
                VERSION_COUNTS[version] += 1

    @task(1)
    def read_count(self):
        self.client.get("/api/count", name="/api/count")

    @task(1)
    def read_version(self):
        self.client.get("/api/version", name="/api/version")


@events.test_start.add_listener
def _reset(environment, **kwargs):
    with _lock:
        VERSION_COUNTS.clear()


@events.test_stop.add_listener
def _report(environment, **kwargs):
    with _lock:
        snapshot = dict(VERSION_COUNTS)
    total = sum(snapshot.values()) or 1

    print("\n=== Versionsverteilung ===")
    for version, count in sorted(snapshot.items()):
        print(f"  {version:>10}: {count:6d}  ({count / total * 100:5.1f} %)")
    print("===============================================\n")
