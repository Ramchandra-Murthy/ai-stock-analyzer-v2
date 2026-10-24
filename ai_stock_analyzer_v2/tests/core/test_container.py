from __future__ import annotations

import unittest

from core.container import bootstrap_container, container
from services.valuation.dispatcher import ValuationDispatcher


class TestServiceContainer(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure container is bootstrapped
        bootstrap_container()

    def test_container_resolution(self) -> None:
        dispatcher = container.resolve("valuation_dispatcher")
        self.assertIsInstance(dispatcher, ValuationDispatcher)

        # Verify engines are registered in the dispatcher
        supported_methods = dispatcher.list_supported_methods()
        self.assertIn("DCF", supported_methods)
        self.assertIn("NAV", supported_methods)
        self.assertIn("SOTP", supported_methods)


if __name__ == "__main__":
    unittest.main()
