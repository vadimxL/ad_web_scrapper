from urllib import parse


def extract_query_params(url: str) -> dict:
    # Extract query parameters from the URL
    params = dict(parse.parse_qsl(parse.urlsplit(url).query))
    return params


def join_query_params(params: dict) -> str:
    # Join the dictionary of query parameters into a string without URL encoding
    return '&'.join(f"{key}={value}" for key, value in params.items())