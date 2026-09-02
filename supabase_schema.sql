create table if not exists public.products (
  id text primary key,
  title text not null,
  type text not null,
  colors jsonb not null default '[]'::jsonb,
  groups_json jsonb not null default '[]'::jsonb,
  size text,
  price numeric,
  description text,
  image text,
  available boolean not null default true,
  published boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.tags (
  id text primary key,
  kind text not null check (kind in ('types', 'colors', 'groups')),
  name text not null,
  created_at timestamptz not null default now(),
  unique (kind, name)
);

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists products_set_updated_at on public.products;
create trigger products_set_updated_at
before update on public.products
for each row execute function public.set_updated_at();
