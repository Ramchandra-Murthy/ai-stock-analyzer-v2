-- Durable AI signal inputs and measured outcomes.
-- Run in the Supabase SQL Editor before enabling the Supabase signal-history backend.
-- The application uses a server-side SUPABASE_SECRET_KEY; do not expose it to clients.

create table if not exists public.ai_signal_history (
    signal_timestamp timestamptz not null,
    symbol text not null,
    exchange text not null,
    record jsonb not null,
    outcome jsonb,
    updated_at timestamptz not null default now(),
    constraint ai_signal_history_signal_key
        unique (signal_timestamp, symbol, exchange)
);

create index if not exists ai_signal_history_symbol_time_idx
    on public.ai_signal_history (symbol, signal_timestamp desc);

alter table public.ai_signal_history enable row level security;

-- No anon/authenticated policies are created. Access is restricted to the
-- server-side secret key used by the Streamlit application.
