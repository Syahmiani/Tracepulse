# Minimal test file for API routes
from tracepulse.app import create_app

def test_health_endpoint():
    app = create_app({"TESTING": True})
    response = app.test_client().get("/api/status/health")
    assert response.status_code == 200
    assert response.json["service"] == "tracepulse"