import re
from jinja2.ext import Extension


def is_semver(value: str) -> bool:
    return bool(re.match(r"^\d+\.\d+\.\d+$", value))


def is_npm_scope(value: str) -> bool:
    if not value:
        return True
    return bool(re.match(r"^@[a-z0-9\-_]+$", value))


def is_valid_email(value: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", value))


class ValidationFilters(Extension):
    def __init__(self, environment=None):
        # Allow instantiation without a Jinja environment for unit tests
        if environment is None:
            # Provide the methods as attributes so tests can call them directly
            self.is_semver = is_semver
            self.is_npm_scope = is_npm_scope
            self.is_valid_email = is_valid_email
            return

        super().__init__(environment)
        environment.filters["is_semver"] = is_semver
        environment.filters["is_npm_scope"] = is_npm_scope
        environment.filters["is_valid_email"] = is_valid_email
