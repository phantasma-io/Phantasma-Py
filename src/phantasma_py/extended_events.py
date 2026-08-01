"""Typed extended-event data carried by ``extendedEvents`` of a transaction answer.

The ``kind`` of the carrying event decides the shape of its ``data``; inside a special resolution
the ``module`` and ``method`` of each call decide the shape of its ``arguments``. Both dispatches
happen while decoding, so a consumer matches on a type instead of walking untyped JSON::

    for event in tx.extended_events:
        if isinstance(event.data, SpecialResolutionData):
            for call in event.data.calls:
                if isinstance(call.arguments, TransferFungibleArguments):
                    use(call.arguments.token, call.arguments.amount)

Two rules keep decoding total, so one unexpected event can never fail a whole block answer:

* a payload whose kind, module or method this build does not model arrives verbatim in
  :class:`UnknownEventData` or :class:`UnrecognizedArguments`;
* a payload that names a modeled shape but does not match it falls back to the same raw carriers
  instead of raising, so a newer node's field changes degrade to raw JSON rather than to a dead
  client. A ``kind`` that names a modeled shape while ``data`` is :class:`UnknownEventData` is how
  a consumer detects that drift.

Numeric fields follow the wire exactly: chain amounts, counts and big-integer ids travel as strings
(JSON numbers lose precision above 2^53), while Carbon-side ids (``carbonTokenId``, ``moduleId``,
``resolutionId``) and timestamps are plain JSON numbers.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ._wire_shapes import ShapeMismatch, decode_shape, shape_to_wire
from .special_resolution_arguments import (
    SpecialResolutionArguments,
    decode_special_resolution_arguments,
)


@dataclass(slots=True)
class TokenCreateData:
    """Data of a ``TokenCreate`` extended event."""

    symbol: str = ""
    max_supply: str = ""
    decimals: int = 0
    is_non_fungible: bool = False
    carbon_token_id: int = 0
    # Metadata values are rendered to strings by the node, so unlike the metadata of a token
    # response they are not VM values here. Keys arrive exactly as the chain stores them.
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TokenSeriesCreateData:
    """Data of a ``TokenSeriesCreate`` extended event."""

    symbol: str = ""
    # Phantasma series id, a big integer rendered as a string.
    series_id: str = ""
    max_mint: int = 0
    max_supply: int = 0
    owner: str = ""
    carbon_token_id: int = 0
    carbon_series_id: int = 0
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class MarketOrderData:
    """Data of an ``OrderCreated``, ``OrderCancelled`` or ``OrderFilled`` extended event.

    The three kinds share one shape; the carrying event's ``kind`` tells them apart.
    """

    base_symbol: str = ""
    quote_symbol: str = ""
    # Phantasma NFT id, a big integer rendered as a string.
    token_id: str = ""
    carbon_base_token_id: int = 0
    carbon_quote_token_id: int = 0
    carbon_instance_id: int = 0
    seller: str = ""
    # On a cancel the node repeats the seller here: that path has no buyer by definition and the
    # payload shape stays stable.
    buyer: str = ""
    price: str = ""
    end_price: str = ""
    start_date: int = 0
    end_date: int = 0
    # Auction type name, for example "Fixed".
    type: str = ""


@dataclass(slots=True)
class SpecialResolutionCall:
    """One call carried by a special resolution.

    ``arguments`` is typed per method: ``module`` and ``method`` decide the shape. ``calls`` carries
    the calls of a nested resolution and is empty everywhere else.
    """

    module_id: int = 0
    module: str = ""
    method_id: int = 0
    method: str = ""
    arguments: SpecialResolutionArguments | None = None
    calls: list[SpecialResolutionCall] = field(default_factory=list)

    @classmethod
    def from_wire(cls, raw: Any) -> SpecialResolutionCall:
        """Reads one call and gives its arguments the type that belongs to the called method.

        Every field is read leniently: a single odd call must not fail the transaction it belongs
        to, so an unreadable id or name falls back to its default exactly as in the C# SDK.
        """
        if not isinstance(raw, Mapping):
            return cls()

        module = _wire_str(raw.get("module"))
        method = _wire_str(raw.get("method"))
        return cls(
            module_id=_wire_int(raw.get("moduleId")),
            module=module,
            method_id=_wire_int(raw.get("methodId")),
            method=method,
            arguments=decode_special_resolution_arguments(module, method, raw.get("arguments")),
            calls=_wire_calls(raw.get("calls")),
        )

    def to_wire(self) -> dict[str, Any]:
        """Writes the call back in the node's wire form, omitting what the node omits."""
        written: dict[str, Any] = {
            "moduleId": self.module_id,
            "module": self.module,
            "methodId": self.method_id,
            "method": self.method,
        }
        if self.arguments is not None:
            written["arguments"] = shape_to_wire(self.arguments)
        if self.calls:
            written["calls"] = [call.to_wire() for call in self.calls]
        return written


@dataclass(slots=True)
class SpecialResolutionData:
    """Data of a ``SpecialResolution`` extended event."""

    resolution_id: int = 0
    # Absent on most resolutions; the node omits it instead of answering null.
    description: str | None = None
    calls: list[SpecialResolutionCall] = field(default_factory=list)

    @classmethod
    def from_wire(cls, raw: Any) -> SpecialResolutionData:
        """Reads the resolution envelope; a payload that is not an object yields the empty one."""
        if not isinstance(raw, Mapping):
            return cls()
        description = raw.get("description")
        return cls(
            resolution_id=_wire_int(raw.get("resolutionId")),
            description=description if isinstance(description, str) else None,
            calls=_wire_calls(raw.get("calls")),
        )

    def to_wire(self) -> dict[str, Any]:
        """Writes the resolution back in the node's wire form, omitting an absent description."""
        written: dict[str, Any] = {"resolutionId": self.resolution_id}
        if self.description is not None:
            written["description"] = self.description
        written["calls"] = [call.to_wire() for call in self.calls]
        return written


@dataclass(slots=True)
class UnknownEventData:
    """Payload of an event kind this build does not model, or of a modeled kind whose payload did
    not match its shape. The parsed JSON is kept as answered."""

    data: Any = None

    def to_wire(self) -> Any:
        """Writes the preserved payload back unchanged."""
        return self.data


EventData = TokenCreateData | TokenSeriesCreateData | MarketOrderData | SpecialResolutionData | UnknownEventData

# Event kind to the shape of its payload. The three market kinds share one shape, exactly as the
# node's event builder emits them.
EVENT_SHAPES: dict[str, type[TokenCreateData | TokenSeriesCreateData | MarketOrderData]] = {
    "TokenCreate": TokenCreateData,
    "TokenSeriesCreate": TokenSeriesCreateData,
    "OrderCreated": MarketOrderData,
    "OrderCancelled": MarketOrderData,
    "OrderFilled": MarketOrderData,
}


def decode_event_data(kind: str, raw: Any) -> EventData | None:
    """Types a raw extended-event payload from the kind of the event that carries it.

    An absent payload yields None; everything else follows the totality rule documented on this
    module.
    """
    if raw is None:
        return None

    if kind == "SpecialResolution":
        return SpecialResolutionData.from_wire(raw)

    shape = EVENT_SHAPES.get(kind)
    if shape is None:
        return UnknownEventData(data=raw)

    try:
        return decode_shape(shape, raw)
    except ShapeMismatch:
        return UnknownEventData(data=raw)


@dataclass(slots=True)
class EventExResult:
    """One extended transaction event returned by current RPC nodes."""

    address: str = ""
    contract: str = ""
    kind: str = ""
    data: EventData | None = None

    @classmethod
    def from_wire(cls, raw: Any) -> EventExResult:
        """Reads the envelope and types the payload; the kind must be read before the data."""
        if not isinstance(raw, Mapping):
            return cls()
        kind = _wire_str(raw.get("kind"))
        return cls(
            address=_wire_str(raw.get("address")),
            contract=_wire_str(raw.get("contract")),
            kind=kind,
            data=decode_event_data(kind, raw.get("data")),
        )

    def to_wire(self) -> dict[str, Any]:
        """Writes the event back in the node's wire form."""
        written: dict[str, Any] = {
            "address": self.address,
            "contract": self.contract,
            "kind": self.kind,
        }
        if self.data is not None:
            written["data"] = shape_to_wire(self.data)
        return written


def _wire_str(value: Any) -> str:
    """Reads a string field; anything else yields the empty string, as in the C# SDK."""
    return value if isinstance(value, str) else ""


def _wire_int(value: Any) -> int:
    """Reads a numeric id field; anything else yields 0, as in the C# SDK."""
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def _wire_calls(value: Any) -> list[SpecialResolutionCall]:
    """Reads a nested call list; anything that is not an array yields no calls."""
    if not isinstance(value, list):
        return []
    return [SpecialResolutionCall.from_wire(item) for item in value]
