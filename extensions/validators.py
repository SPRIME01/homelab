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
    """
    Jinja2 extension to register filters used by Copier templates.

    Register this in copier.yml via _jinja_extensions:
        - extensions/validators.py:ValidationFilters

    These filters can be used within `validator:` expressions in `copier.yml`.
    """

    def __init__(self, environment=None):
        """
        If `environment` is None this behaves like a lightweight wrapper
        exposing validation functions as attributes - this is useful for
        unit tests that import `ValidationFilters` and call methods
        directly. If an environment is provided, this registers the
        filters in the Jinja2 environment.
        """
        if environment is None:
            self.is_semver = is_semver
            self.is_npm_scope = is_npm_scope
            self.is_valid_email = is_valid_email
            return

        super().__init__(environment)
        # Register filters here so they are available inside copier templates
        environment.filters["is_semver"] = is_semver
        environment.filters["is_npm_scope"] = is_npm_scope
        environment.filters["is_valid_email"] = is_valid_email
