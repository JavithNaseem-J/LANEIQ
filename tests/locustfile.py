"""
Locust load test — 10 concurrent users submitting /optimize and polling /status.
Run with: locust -f tests/locustfile.py --headless -u 10 -r 2 --run-time 2m
"""
import time
from locust import HttpUser, task, between

BRIEF = "Ship 500 kg of electronics from Chennai to Jebel Ali by June 20, 2026. Prefer air freight."


class FreightUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def optimize_and_poll(self):
        # Submit
        with self.client.post(
            "/optimize",
            json={"shipment_brief": BRIEF},
            catch_response=True,
            name="/optimize",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Submit failed: {resp.status_code}")
                return
            task_id = resp.json().get("task_id")
            if not task_id:
                resp.failure("No task_id in response")
                return
            resp.success()

        # Poll until done (max 90s)
        deadline = time.time() + 90
        while time.time() < deadline:
            with self.client.get(
                f"/status/{task_id}",
                catch_response=True,
                name="/status/{task_id}",
            ) as poll:
                if poll.status_code != 200:
                    poll.failure(f"Poll failed: {poll.status_code}")
                    return
                state = poll.json().get("state")
                if state == "success":
                    poll.success()
                    return
                elif state == "failure":
                    poll.failure("Task failed")
                    return
                poll.success()  # still pending — mark as ok
            time.sleep(2)

    @task(weight=2)
    def health_check(self):
        self.client.get("/health", name="/health")
