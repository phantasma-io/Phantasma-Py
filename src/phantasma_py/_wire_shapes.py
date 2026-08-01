"""Strict decoding and encoding of the modeled wire shapes.

The response models in :mod:`phantasma_py.rpc` are decoded leniently: a field that does not match
its annotation is passed through, because a response model must not fail a whole answer over one
odd field. The extended-event tree needs the opposite contract. There, a payload that does not
match its modeled shape has to be *detected*, so that the caller can keep the JSON verbatim instead
of handing out a half-empty object that a consumer cannot tell apart from a genuinely empty one.

So these helpers validate every field against its annotation and raise :class:`ShapeMismatch` on
the first disagreement, while a missing field simply keeps the dataclass default - the same
contract the Rust and Go ports get from serde and encoding/json.
"""

from __future__ import annotations

import types
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from typing import Any, TypeVar, Union, cast, get_args, get_origin, get_type_hints

from .vm_value import VmValue

T = TypeVar("T")


class ShapeMismatch(Exception):
    """Raised when a payload does not match the shape it was decoded against."""


def snake_to_camel(value: str) -> str:
    """Converts a Python field name to the camelCase name the node writes."""
    head, *rest = value.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def wire_name_of(field_name: str, metadata: Mapping[str, Any]) -> str:
    """The wire name of one field: the camelCase form, unless the field declares an override.

    The override exists for wire names that are Python keywords: ``from`` is spelled ``from_`` in
    the models and cannot be derived from the field name.
    """
    override = metadata.get("wire")
    return str(override) if override else snake_to_camel(field_name)


def decode_shape(cls: type[T], raw: Any) -> T:
    """Decodes one modeled shape, raising :class:`ShapeMismatch` when the payload is not that shape."""
    if not isinstance(raw, Mapping):
        raise ShapeMismatch(f"{cls.__name__} expects a JSON object")

    hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}
    for field_info in fields(cast(Any, cls)):
        wire_name = wire_name_of(field_info.name, field_info.metadata)
        if wire_name in raw:
            value = raw[wire_name]
        elif field_info.name in raw:
            value = raw[field_info.name]
        else:
            continue
        kwargs[field_info.name] = _decode_field(hints[field_info.name], value, f"{cls.__name__}.{field_info.name}")
    return cls(**kwargs)


def _decode_field(annotation: Any, value: Any, path: str) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (Union, types.UnionType):
        optional = [argument for argument in args if argument is not type(None)]
        if len(optional) != 1:
            raise ShapeMismatch(f"{path}: unions of several shapes are not modeled")
        if value is None:
            return None
        return _decode_field(optional[0], value, path)

    if annotation is VmValue:
        return VmValue.from_wire(value)

    if annotation is str:
        if not isinstance(value, str):
            raise ShapeMismatch(f"{path}: expected a string, got {type(value).__name__}")
        return value

    if annotation is bool:
        if not isinstance(value, bool):
            raise ShapeMismatch(f"{path}: expected a boolean, got {type(value).__name__}")
        return value

    if annotation is int:
        # bool is a subclass of int in Python, so it has to be rejected explicitly.
        if isinstance(value, bool) or not isinstance(value, int):
            raise ShapeMismatch(f"{path}: expected a number, got {type(value).__name__}")
        return value

    if origin is list:
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            raise ShapeMismatch(f"{path}: expected an array, got {type(value).__name__}")
        return [_decode_field(args[0], item, f"{path}[]") for item in value]

    if origin is dict:
        if not isinstance(value, Mapping):
            raise ShapeMismatch(f"{path}: expected an object, got {type(value).__name__}")
        return {str(name): _decode_field(args[1], item, f"{path}.{name}") for name, item in value.items()}

    if is_dataclass(annotation):
        return decode_shape(cast(type[Any], annotation), value)

    raise ShapeMismatch(f"{path}: {annotation!r} is not a modeled shape")


def shape_to_wire(value: Any) -> Any:
    """Writes a decoded shape back in the node's wire form.

    Absent optional fields are omitted rather than written as null, which is what the node's
    serializer does; a type that carries preserved JSON writes it back verbatim through its own
    ``to_wire``.
    """
    to_wire = getattr(value, "to_wire", None)
    if callable(to_wire):
        return to_wire()

    if is_dataclass(value) and not isinstance(value, type):
        written: dict[str, Any] = {}
        for field_info in fields(value):
            field_value = getattr(value, field_info.name)
            if field_value is None:
                continue
            written[wire_name_of(field_info.name, field_info.metadata)] = shape_to_wire(field_value)
        return written

    if isinstance(value, Mapping):
        return {str(name): shape_to_wire(item) for name, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [shape_to_wire(item) for item in value]

    return value
