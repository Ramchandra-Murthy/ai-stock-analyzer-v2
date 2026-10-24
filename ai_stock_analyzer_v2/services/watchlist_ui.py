"""Single-owner watchlist adapter; no login or email identity is required."""

from services.watchlist_service import (
    OWNER_ID,
    add_symbol,
    create_watchlist,
    list_symbols,
    list_watchlists,
)

DEFAULT_WATCHLIST_NAME = "My Watchlist"


def get_or_create_default_watchlist(
    user=None, default_symbols: list[str] | None = None
) -> tuple[str, int, list[str]]:
    """Return the one shared watchlist, creating it and optional defaults if needed.

    The optional user argument is retained for compatibility with older callers
    but is deliberately ignored: all app sessions use the same personal list.
    """
    del user
    watchlists = list_watchlists(OWNER_ID)
    if not watchlists:
        watchlist_id = create_watchlist(OWNER_ID, DEFAULT_WATCHLIST_NAME)
        for symbol in default_symbols or []:
            add_symbol(OWNER_ID, watchlist_id, symbol)
        return OWNER_ID, watchlist_id, list_symbols(OWNER_ID, watchlist_id)

    watchlist_id = int(watchlists[0]["id"])
    existing_symbols = set(list_symbols(OWNER_ID, watchlist_id))
    for watchlist in watchlists[1:]:
        old_id = int(watchlist["id"])
        for symbol in list_symbols(OWNER_ID, old_id):
            if symbol not in existing_symbols:
                add_symbol(OWNER_ID, watchlist_id, symbol)
                existing_symbols.add(symbol)
    return OWNER_ID, watchlist_id, list_symbols(OWNER_ID, watchlist_id)
