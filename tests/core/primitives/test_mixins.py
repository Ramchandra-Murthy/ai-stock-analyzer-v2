from __future__ import annotations

import pytest

from core.primitives.mixins import ComparableMixin, SerializableMixin


def test_mixins_not_implemented() -> None:
    s = SerializableMixin()
    with pytest.raises(NotImplementedError):
        s.to_dict()

    c = ComparableMixin()
    with pytest.raises(NotImplementedError):
        c._get_comparison_value()
