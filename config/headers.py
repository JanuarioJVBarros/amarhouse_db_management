def build_headers(token=None, cookie=None):
    headers = {
        "content-type": "application/json",
        "accept": "application/json",
        "apollo-require-preflight": "true",
    }

    if token:
        headers["beeevo-token"] = token

    if cookie:
        headers["cookie"] = cookie

    return headers