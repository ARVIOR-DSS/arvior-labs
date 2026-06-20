import os
import requests

API_BASE_URL = os.getenv(
    "ARVIOR_API_BASE_URL",
    "https://arvior-api-b8g6h4awe2aea0b2.westeurope-01.azurewebsites.net",
)


def check_api_health() -> tuple[bool, str]:
    url = f"{API_BASE_URL}/docs"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return True, f"ARVIOR API docs are reachable at {API_BASE_URL}."
        return False, f"API returned status code {response.status_code} at {API_BASE_URL}."
    except requests.RequestException as exc:
        return False, f"Could not reach ARVIOR API at {API_BASE_URL}: {exc}"


def run_arvior(request_json: dict) -> dict:
    url = f"{API_BASE_URL}/run-arvior"
    response = requests.post(url, json=request_json, timeout=180)
    response.raise_for_status()
    return response.json()