import re

def validate_username(username: str) -> bool:
    if len(username) < 3 or len(username) > 20:
        return False
    if not re.match("^[a-zA-Z0-9_]+$", username):
        return False
    return True

def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    return True
