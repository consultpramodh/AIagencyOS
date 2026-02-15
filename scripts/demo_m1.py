import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


def main() -> None:
    client = TestClient(app)

    owner_login = client.post(
        "/login",
        data={"email": "owner@demo.local", "password": "demo1234"},
        follow_redirects=False,
    )
    print("Owner login status:", owner_login.status_code)

    dashboard = client.get("/?tenant_id=1")
    print("Dashboard status:", dashboard.status_code)

    create_client = client.post(
        "/clients?tenant_id=1",
        data={"name": "Demo Script Client"},
        follow_redirects=False,
    )
    print("Create client status:", create_client.status_code)

    viewer = TestClient(app)
    viewer_login = viewer.post(
        "/login",
        data={"email": "viewer@demo.local", "password": "demo1234"},
        follow_redirects=False,
    )
    print("Viewer login status:", viewer_login.status_code)

    blocked = viewer.get("/?tenant_id=2")
    print("Viewer cross-tenant status:", blocked.status_code)

    print("M1 demo completed")


if __name__ == "__main__":
    main()
