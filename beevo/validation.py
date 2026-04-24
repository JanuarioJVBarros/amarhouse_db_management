from collections.abc import Mapping

from beevo.exceptions import BeevoValidationError


def require_mapping(value, context):
    if not isinstance(value, Mapping):
        raise BeevoValidationError(f"{context} must be a mapping/dict. Got: {type(value).__name__}")
    return value


def require_list(value, context):
    if not isinstance(value, list):
        raise BeevoValidationError(f"{context} must be a list. Got: {type(value).__name__}")
    return value


def require_fields(mapping, fields, context):
    data = require_mapping(mapping, context)
    missing = [field for field in fields if field not in data]
    if missing:
        raise BeevoValidationError(f"{context} is missing required field(s): {missing}")
    return data


def require_path(mapping, path, context):
    current = require_mapping(mapping, context)
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            joined_path = ".".join(path)
            raise BeevoValidationError(f"{context} is missing required path: {joined_path}")
        current = current[key]
    return current


def require_value(value, context):
    if value is None:
        raise BeevoValidationError(f"{context} cannot be null")
    return value
