-- ============================================================
-- EvoTrade — Database Migration
-- Run this once in Supabase SQL Editor to create all tables.
-- ============================================================

-- ── Shared updated_at trigger ────────────────────────────────
create or replace function evotrade_set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ── 1. Strategies ────────────────────────────────────────────
create table if not exists evotrade_strategies (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid references auth.users(id) on delete cascade,
  genes         jsonb not null,
  status        text not null default 'candidate'
                  check (status in ('candidate','shadow','live','retired','rolled_back')),
  origin        text not null default 'evolution',
  fitness       numeric(10,6),
  metadata      jsonb default '{}',
  activated_at  timestamptz,
  retired_at    timestamptz,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);
create index if not exists idx_evotrade_strategies_user on evotrade_strategies(user_id);
create index if not exists idx_evotrade_strategies_status on evotrade_strategies(status);

drop trigger if exists evotrade_strategies_updated_at on evotrade_strategies;
create trigger evotrade_strategies_updated_at
  before update on evotrade_strategies
  for each row execute function evotrade_set_updated_at();

alter table evotrade_strategies enable row level security;
create policy "owner_all" on evotrade_strategies
  for all using (auth.uid() = user_id);
create policy "service_insert" on evotrade_strategies
  for insert with check (true);

-- ── 2. Evolution Runs ────────────────────────────────────────
create table if not exists evotrade_evolution_runs (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid references auth.users(id) on delete cascade,
  symbol              text not null,
  risk_profile        text not null,
  n_generations       int not null,
  population_size     int not null,
  status              text not null default 'running'
                        check (status in ('running','completed','failed')),
  final_alpha_gene_id uuid references evotrade_strategies(id),
  fitness_history     jsonb default '[]',
  completed_at        timestamptz,
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);
create index if not exists idx_evotrade_runs_user on evotrade_evolution_runs(user_id);

drop trigger if exists evotrade_evolution_runs_updated_at on evotrade_evolution_runs;
create trigger evotrade_evolution_runs_updated_at
  before update on evotrade_evolution_runs
  for each row execute function evotrade_set_updated_at();

alter table evotrade_evolution_runs enable row level security;
create policy "owner_all" on evotrade_evolution_runs
  for all using (auth.uid() = user_id);

-- ── 3. Generation Results ────────────────────────────────────
create table if not exists evotrade_generation_results (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid references auth.users(id) on delete cascade,
  run_id       uuid references evotrade_evolution_runs(id) on delete cascade,
  generation   int not null,
  candidates   jsonb default '[]',
  top_3        jsonb default '[]',
  alpha_gene   jsonb,
  best_fitness numeric(10,6),
  avg_fitness  numeric(10,6),
  created_at   timestamptz default now()
);
create index if not exists idx_evotrade_genresults_run on evotrade_generation_results(run_id);

alter table evotrade_generation_results enable row level security;
create policy "owner_all" on evotrade_generation_results
  for all using (auth.uid() = user_id);

-- ── 4. Backtest Results ──────────────────────────────────────
create table if not exists evotrade_backtest_results (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid references auth.users(id) on delete cascade,
  strategy_id       uuid references evotrade_strategies(id) on delete cascade,
  sharpe_ratio      numeric(10,4),
  max_drawdown_pct  numeric(10,4),
  win_rate          numeric(6,4),
  trades            int,
  profit_factor     numeric(10,4),
  fitness_score     numeric(10,6),
  total_return_pct  numeric(10,4),
  raw_metrics       jsonb default '{}',
  created_at        timestamptz default now()
);

alter table evotrade_backtest_results enable row level security;
create policy "owner_all" on evotrade_backtest_results
  for all using (auth.uid() = user_id);

-- ── 5. Monte Carlo Results ───────────────────────────────────
create table if not exists evotrade_monte_carlo_results (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid references auth.users(id) on delete cascade,
  strategy_id           uuid references evotrade_strategies(id) on delete cascade,
  paths                 int,
  survivability_pct     numeric(6,2),
  tail_dd_95_pct        numeric(10,4),
  worst_case_return_pct numeric(10,4),
  robust_fitness        numeric(10,6),
  raw_metrics           jsonb default '{}',
  created_at            timestamptz default now()
);

alter table evotrade_monte_carlo_results enable row level security;
create policy "owner_all" on evotrade_monte_carlo_results
  for all using (auth.uid() = user_id);

-- ── 6. AI Reasoning Cards ────────────────────────────────────
create table if not exists evotrade_ai_reasoning_cards (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid references auth.users(id) on delete cascade,
  run_id        uuid references evotrade_evolution_runs(id) on delete set null,
  generation    int,
  strategy_id   uuid references evotrade_strategies(id) on delete set null,
  reasoning_json jsonb not null,
  model         text,
  source        text default 'fallback',
  latency_s     numeric(8,3),
  created_at    timestamptz default now()
);

alter table evotrade_ai_reasoning_cards enable row level security;
create policy "owner_all" on evotrade_ai_reasoning_cards
  for all using (auth.uid() = user_id);

-- ── 7. Trades ────────────────────────────────────────────────
create table if not exists evotrade_trades (
  id               uuid primary key default gen_random_uuid(),
  user_id          uuid references auth.users(id) on delete cascade,
  strategy_id      uuid references evotrade_strategies(id) on delete set null,
  symbol           text not null,
  side             text not null check (side in ('buy','sell')),
  type             text default 'MARKET',
  qty              numeric(20,8),
  fill_price       numeric(20,8),
  mark_price       numeric(20,8),
  fee_usdt         numeric(20,8),
  slip_bps_used    numeric(8,2),
  status           text default 'filled',
  broker_order_id  text,
  is_paper         boolean default true,
  regime_at_entry  text,
  metadata         jsonb default '{}',
  created_at       timestamptz default now()
);
create index if not exists idx_evotrade_trades_user on evotrade_trades(user_id);
create index if not exists idx_evotrade_trades_symbol on evotrade_trades(symbol, created_at desc);

alter table evotrade_trades enable row level security;
create policy "owner_all" on evotrade_trades
  for all using (auth.uid() = user_id);

-- ── 8. Risk Events ───────────────────────────────────────────
create table if not exists evotrade_risk_events (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  event_type  text not null,
  reason      text,
  payload     jsonb default '{}',
  created_at  timestamptz default now()
);

alter table evotrade_risk_events enable row level security;
create policy "owner_all" on evotrade_risk_events
  for all using (auth.uid() = user_id);

-- ── 9. Audit Logs ────────────────────────────────────────────
create table if not exists evotrade_audit_logs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  audit_id    text not null unique,
  event_type  text not null,
  payload     jsonb default '{}',
  prev_hash   text,
  hash        text not null,
  created_at  timestamptz default now()
);
create index if not exists idx_evotrade_audit_created on evotrade_audit_logs(created_at desc);

alter table evotrade_audit_logs enable row level security;
create policy "owner_read" on evotrade_audit_logs
  for select using (auth.uid() = user_id);

-- ── 10. Positions ────────────────────────────────────────────
create table if not exists evotrade_positions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  symbol      text not null,
  qty         numeric(20,8) not null default 0,
  avg_price   numeric(20,8),
  is_paper    boolean default true,
  updated_at  timestamptz default now(),
  unique (user_id, symbol, is_paper)
);

alter table evotrade_positions enable row level security;
create policy "owner_all" on evotrade_positions
  for all using (auth.uid() = user_id);

-- ── 11. Broker Connections ───────────────────────────────────
create table if not exists evotrade_broker_connections (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid references auth.users(id) on delete cascade,
  broker          text not null,
  envelope_v      int default 1,
  envelope_alg    text default 'AES-256-GCM',
  envelope_nonce  text,
  envelope_ct     text,
  envelope_aad    text,
  is_active       boolean default true,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

drop trigger if exists evotrade_broker_connections_updated_at on evotrade_broker_connections;
create trigger evotrade_broker_connections_updated_at
  before update on evotrade_broker_connections
  for each row execute function evotrade_set_updated_at();

alter table evotrade_broker_connections enable row level security;
create policy "owner_all" on evotrade_broker_connections
  for all using (auth.uid() = user_id);

-- ── 12. Dashboard Events ─────────────────────────────────────
create table if not exists evotrade_dashboard_events (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  event_type  text not null,
  payload     jsonb default '{}',
  created_at  timestamptz default now()
);
create index if not exists idx_evotrade_dash_created on evotrade_dashboard_events(created_at desc);

alter table evotrade_dashboard_events enable row level security;
create policy "owner_all" on evotrade_dashboard_events
  for all using (auth.uid() = user_id);
