from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.primitives.mixins import SerializableMixin


@dataclass(frozen=True)
class ValueObject(SerializableMixin):
    """Base immutable value object class for all financial primitives."""

    def to_dict(self) -> dict[str, Any]:
        """Default dictionary representation using dataclass fields."""
        import dataclasses

        return dataclasses.asdict(self)

    def to_json(self) -> str:
        """Serialize value object to a JSON string."""

        class DecimalEncoder(json.JSONEncoder):
            def default(self, o: Any) -> Any:
                if isinstance(o, Decimal):
                    return str(o)
                return super().default(o)

        return json.dumps(self.to_dict(), cls=DecimalEncoder)
