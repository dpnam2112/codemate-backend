from urllib.parse import urlparse

def singleton(cls):
    """
    A decorator function that ensures a class has only one instance and provides a global point of access to it.
    """

    instances = {}

    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return wrapper

def parse_postgres_connection_string(conn_str):
    parsed_url = urlparse(conn_str)
    
    host = parsed_url.hostname
    port = parsed_url.port
    database = parsed_url.path.lstrip('/')  # Remove leading '/'
    
    return {
        "host": host,
        "port": port,
        "database": database
    }

