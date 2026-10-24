# Open single-owner watchlist

The Market and Scanner modules use one shared watchlist without Google sign-in,
email identity, or OAuth configuration. This is intended for a personal app where
the operator accepts that anyone who can access the deployed URL can view or edit
the watchlist. Do not use this unauthenticated mode for confidential information.

## Saved stock details

Each symbol can store entry price, stop-loss, target price, quantity, investment
type, purchase/planned-entry date, notes, status, and created/updated timestamps.
Market data quotes are fetched separately; manually entered investment levels are
not represented as verified live prices. Market and Scanner share the same symbols.

## Durable storage

Set `WATCHLIST_DATABASE_PATH` to a writable path on durable storage supported by
your hosting platform. The default local SQLite file may be lost when an ephemeral
container restarts or redeploys. Back up the database according to the host's
storage guarantees.

The database upgrade consolidates legacy per-identity watchlists into one list,
retaining symbols and the first saved record for duplicate symbols. Make a backup
of an existing database before deploying the migration.

## Verify after deployment

1. Open Market without signing in.
2. Add a test symbol and save entry price, stop-loss, target, quantity, date, notes,
   investment type, and status.
3. Refresh and verify the saved details remain.
4. Open Scanner and confirm the same symbols are available in Personal Watchlist.
5. Restart/redeploy and verify persistence after durable storage is configured.
