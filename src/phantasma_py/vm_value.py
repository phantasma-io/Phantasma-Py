"""Values decoded from VM storage, as carried by token metadata and NFT properties."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class VmValue:
    """A value decoded from VM storage: a scalar, an array, or a struct.

    VM values are dynamically typed, so the wire carries the plain JSON value - a string, an array
    or an object - and the shape itself says which of the three it is. Nothing is packed into a
    JSON string, which is what these values used to be before the 2026-08 node series.

    Exactly one of :attr:`text`, :attr:`items` and :attr:`fields` is set. Scalars are always text:
    chain numbers are big integers and JSON numbers lose precision above 2^53, so the node writes
    them as decimal strings, and byte values arrive as hex. Struct field names arrive exactly as
    the chain stores them; the node does not rename dictionary keys.

    The default value is an empty scalar, which is also what an explicit JSON null decodes to.
    """

    text: str | None = ""
    items: tuple[VmValue, ...] | None = None
    fields: Mapping[str, VmValue] | None = field(default=None)

    @classmethod
    def of_text(cls, text: str) -> VmValue:
        """Builds a scalar value."""
        return cls(text=text)

    @classmethod
    def of_items(cls, items: Iterable[VmValue]) -> VmValue:
        """Builds an array value."""
        return cls(text=None, items=tuple(items))

    @classmethod
    def of_fields(cls, fields_: Mapping[str, VmValue]) -> VmValue:
        """Builds a struct value."""
        return cls(text=None, fields=dict(fields_))

    @property
    def is_text(self) -> bool:
        """True when this is a scalar."""
        return self.text is not None

    def as_text(self) -> str | None:
        """Returns the scalar content, or None for an array or a struct."""
        return self.text

    def as_items(self) -> tuple[VmValue, ...] | None:
        """Returns the array elements, or None for a scalar or a struct."""
        return self.items

    def as_fields(self) -> Mapping[str, VmValue] | None:
        """Returns the struct fields, or None for a scalar or an array."""
        return self.fields

    def get(self, name: str) -> VmValue | None:
        """Returns one field of a struct, or None for a scalar, an array, or a missing field."""
        if self.fields is None:
            return None
        return self.fields.get(name)

    def __str__(self) -> str:
        """The scalar content; an array or a struct renders as the empty string, as in the C# SDK."""
        return self.text or ""

    @classmethod
    def from_wire(cls, value: Any) -> VmValue:
        """Maps one already-parsed JSON value onto the three VM shapes.

        Numbers and booleans are normalized to their JSON text: the node writes every scalar as a
        string, but a response from an older node - or a hand-written one - can still carry them
        untyped, and failing the whole answer over that would be worse than normalizing it. An
        explicit null becomes an empty scalar; the node omits empty values instead of answering
        null.

        Nesting depth is bounded by the JSON parser itself, which rejects input nested deeper than
        its own recursion limit before anything reaches this method.
        """
        if isinstance(value, str):
            return cls.of_text(value)
        if isinstance(value, Mapping):
            return cls.of_fields({str(name): cls.from_wire(item) for name, item in value.items()})
        if isinstance(value, (list, tuple)):
            return cls.of_items([cls.from_wire(item) for item in value])
        if value is None:
            return cls.of_text("")
        if isinstance(value, bool):
            return cls.of_text("true" if value else "false")
        return cls.of_text(str(value))

    def to_wire(self) -> Any:
        """Writes the value back as the plain JSON it represents."""
        if self.items is not None:
            return [item.to_wire() for item in self.items]
        if self.fields is not None:
            return {name: item.to_wire() for name, item in self.fields.items()}
        return self.text
