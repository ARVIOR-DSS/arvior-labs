import requests


API_BASE_URL = "https://arvior-api-b8g6h4awe2aea0b2.westeurope-01.azurewebsites.net"


def check_api_health() -> tuple[bool, str]:
    """
    Check whether the deployed ARVIOR API is reachable.
    """
    url = f"{API_BASE_URL}/docs"

    try:
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            return True, "ARVIOR API docs are reachable."

        return False, f"API returned status code {response.status_code}."

    except requests.RequestException as exc:
        return False, f"Could not reach ARVIOR API: {exc}"


def run_arvior(request_json: dict) -> dict:
    """
    Send an ARVIOR model request to the deployed API.
    """
    url = f"{API_BASE_URL}/run-arvior"

    response = requests.post(
        url,
        json=request_json,
        timeout=120,
    )

    response.raise_for_status()
    return response.json()