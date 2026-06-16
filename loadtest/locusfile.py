from locust import HttpUser, task, between

class NativeToUser(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(0, 0.2)


    @task
    def login(self):
        self.client.post("/api/v1/auth/login", data={"username": "loadtest_user", "password": "loadtest_user"})