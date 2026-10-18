"""
Integration tests for routes.py.

They call the real API started by compose.test.yaml (real PostgreSQL, real Redis).

Run:
    docker compose -f compose.test.yaml up -d --build
    pip install pytest requests
    pytest -v
"""
import base64
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.getenv("TEST_API_URL", "http://localhost:5000")

# Smallest valid PNG (1x1 pixel), so we do not need Pillow in the test environment
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


# helpers

@pytest.fixture(scope="session", autouse=True)
def wait_for_api():
    """Wait until the API and its dependencies are ready (max 30 s)."""
    for _ in range(30):
        try:
            if requests.get(f"{BASE_URL}/health/ready", timeout=2).status_code == 200:
                return
        except requests.ConnectionError:
            pass
        time.sleep(1)
    pytest.fail("API is not ready: check `docker compose -f compose.test.yaml ps`")


def upload(filename="test.png", content=PNG_BYTES, **form):
    """Send an upload request and return the response."""
    files = {"image": (filename, content, "image/png")}
    return requests.post(f"{BASE_URL}/upload", files=files, data=form, timeout=5)


@pytest.fixture
def image_id():
    """Upload a valid image and return its id."""
    response = upload(filter="blur", width=100, height=100)
    assert response.status_code == 202
    return response.json()["image_id"]


# health checks

def test_live():
    response = requests.get(f"{BASE_URL}/health/live", timeout=2)
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_ready():
    response = requests.get(f"{BASE_URL}/health/ready", timeout=5)
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


# upload

def test_upload_page():
    response = requests.get(f"{BASE_URL}/upload", timeout=5)
    assert response.status_code == 200
    assert "text/html" in response.headers["Content-Type"]


def test_upload_ok():
    response = upload(filter="blur", width=200, height=150)
    assert response.status_code == 202
    assert uuid.UUID(response.json()["image_id"])  # valid UUID


def test_upload_without_image():
    response = requests.post(f"{BASE_URL}/upload", data={"filter": "none"}, timeout=5)
    assert response.status_code == 400


def test_upload_unsupported_extension():
    response = upload(filename="notes.txt", content=b"hello")
    assert response.status_code == 400


def test_upload_unknown_filter():
    response = upload(filter="does-not-exist")
    assert response.status_code == 400


def test_upload_invalid_width():
    response = upload(width="abc", height=100)
    assert response.status_code == 400


@pytest.mark.parametrize("width,height", [(0, 100), (100, 0), (-5, 100), (99999, 100)])
def test_upload_size_out_of_range(width, height):
    response = upload(width=width, height=height)
    assert response.status_code == 400


# status

def test_status_of_uploaded_image(image_id):
    response = requests.get(f"{BASE_URL}/status/{image_id}", timeout=5)
    assert response.status_code == 200
    assert "status" in response.json()


def test_status_unknown_id():
    response = requests.get(f"{BASE_URL}/status/{uuid.uuid4()}", timeout=5)
    assert response.status_code == 404


# files

def test_original_file_is_served(image_id):
    # The server stores the file as <image_id>.<extension>
    response = requests.get(f"{BASE_URL}/files/originals/{image_id}.png", timeout=5)
    assert response.status_code == 200
    assert response.content == PNG_BYTES


def test_original_file_not_found():
    response = requests.get(f"{BASE_URL}/files/originals/{uuid.uuid4()}.png", timeout=5)
    assert response.status_code == 404


def test_processed_file_not_found():
    response = requests.get(f"{BASE_URL}/files/processed/{uuid.uuid4()}.png", timeout=5)
    assert response.status_code == 404


# delete / restore

def test_delete_then_restore(image_id):
    # Delete
    response = requests.delete(f"{BASE_URL}/images/{image_id}", timeout=5)
    assert response.status_code == 200
    assert response.json()["task_id"] == image_id

    # Deleting twice is a conflict
    response = requests.delete(f"{BASE_URL}/images/{image_id}", timeout=5)
    assert response.status_code == 409

    # Restore
    response = requests.post(f"{BASE_URL}/images/{image_id}/restore", timeout=5)
    assert response.status_code == 200
    assert response.json()["task_id"] == image_id


def test_restore_not_deleted_image(image_id):
    response = requests.post(f"{BASE_URL}/images/{image_id}/restore", timeout=5)
    assert response.status_code == 409


def test_delete_unknown_id():
    response = requests.delete(f"{BASE_URL}/images/{uuid.uuid4()}", timeout=5)
    assert response.status_code == 404


def test_restore_unknown_id():
    response = requests.post(f"{BASE_URL}/images/{uuid.uuid4()}/restore", timeout=5)
    assert response.status_code == 404


# pages

@pytest.mark.parametrize("path", ["/", "/gallery", "/trash"])
def test_pages_load(path):
    response = requests.get(f"{BASE_URL}{path}", timeout=5)
    assert response.status_code == 200
    assert "text/html" in response.headers["Content-Type"]