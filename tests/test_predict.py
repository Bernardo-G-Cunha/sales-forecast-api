from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_predict_success():
    response = client.post(
        "/predict",
        json={
            "store": 1,
            "date": "2015-07-31",
            "promo": True,
            "state_holiday": "0",
            "school_holiday": False,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert "predicted_sales" in body
    assert isinstance(body["predicted_sales"], int)


def test_store_not_found():
    response = client.post(
        "/predict",
        json={
            "store": 999999,
            "date": "2015-07-31",
            "promo": True,
            "state_holiday": "0",
            "school_holiday": False,
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Store 999999 not found."
    }


def test_invalid_schema():
    response = client.post(
        "/predict",
        json={
            "store": "abc",
            "date": "banana",
            "promo": 2,
            "state_holiday": "x",
            "school_holiday": "talvez",
        },
    )

    assert response.status_code == 422


def test_bool_coercion():
    response = client.post(
        "/predict",
        json={
            "store": 1,
            "date": "2015-07-31",
            "promo": 1,
            "state_holiday": "0",
            "school_holiday": 0,
        },
    )

    assert response.status_code == 200

    assert "predicted_sales" in response.json()