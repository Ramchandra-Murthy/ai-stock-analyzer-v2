-- Personal single-watchlist schema for Supabase.
-- Run in Supabase SQL Editor before enabling the Supabase backend.
-- Keep RLS enabled and do not create anon/authenticated policies: the app uses
-- its server-side SUPABASE_SECRET_KEY, which must never be committed to Git.

alter table public.stock_watchlist
    add column if not exists investment_type text not null default 'Other',
    add column if not exists purchase_date date,
    add column if not exists status text not null default 'Watching',
    add column if not exists position integer not null default 0,
    add column if not exists asset_category text not null default 'Stocks / F&O',
    add column if not exists asset_details jsonb not null default '{}'::jsonb;

-- One shared list: each symbol can appear only once.
create unique index if not exists stock_watchlist_symbol_unique
    on public.stock_watchlist (upper(symbol));

create index if not exists stock_watchlist_position_idx
    on public.stock_watchlist (position, symbol);

alter table public.stock_watchlist enable row level security;

-- No public policies are intentionally created. Server-side requests must use
-- SUPABASE_SECRET_KEY; never expose it in browser code or a public repository.
