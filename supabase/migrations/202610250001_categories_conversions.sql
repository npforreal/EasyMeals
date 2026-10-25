-- EasyMeals Migration: Categories, Default Units, and Ingredient Conversions
-- Migration: 202610250001_categories_conversions.sql

-- 1. Ingredient Categories Table
create table if not exists public.ingredient_categories (
  id text primary key,
  name text not null,
  name_vi text not null,
  display_order integer not null default 0,
  created_at timestamptz not null default now()
);

-- Seed standard categories
insert into public.ingredient_categories (id, name, name_vi, display_order) values
  ('thit', 'Thịt', 'Thịt', 1),
  ('gia_cam', 'Gia cầm', 'Gia cầm', 2),
  ('hai_san', 'Hải sản', 'Hải sản', 3),
  ('trung_sua', 'Trứng & Sữa', 'Trứng & Sữa', 4),
  ('rau_cu', 'Rau củ', 'Rau củ', 5),
  ('cu_qua', 'Củ quả', 'Củ quả', 6),
  ('gao_bot_mi', 'Gạo, bột & mì', 'Gạo, bột & mì', 7),
  ('gia_vi', 'Gia vị', 'Gia vị', 8),
  ('nuoc_cham_dau', 'Nước chấm & dầu ăn', 'Nước chấm & dầu ăn', 9),
  ('khac', 'Khác', 'Khác', 10)
on conflict (id) do update set
  name = excluded.name,
  name_vi = excluded.name_vi,
  display_order = excluded.display_order;

-- 2. Alter Ingredients to add default_unit and constraints
do $$
begin
  if not exists (
    select 1 from information_schema.columns 
    where table_schema = 'public' and table_name = 'ingredients' and column_name = 'default_unit'
  ) then
    alter table public.ingredients add column default_unit public.quantity_unit not null default 'g';
  end if;
end $$;

-- Add check constraint for category if not already present
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'ingredients_category_check'
  ) then
    alter table public.ingredients add constraint ingredients_category_check
      check (category in ('thit', 'gia_cam', 'hai_san', 'trung_sua', 'rau_cu', 'cu_qua', 'gao_bot_mi', 'gia_vi', 'nuoc_cham_dau', 'khac'));
  end if;
end $$;

-- 3. Ingredient Conversions Table (for Gạo <-> Cơm, etc.)
create table if not exists public.ingredient_conversions (
  id uuid primary key default gen_random_uuid(),
  from_ingredient_id uuid not null references public.ingredients(id) on delete cascade,
  to_ingredient_id uuid not null references public.ingredients(id) on delete cascade,
  ratio numeric(12,4) not null check (ratio > 0),
  from_unit public.quantity_unit not null,
  to_unit public.quantity_unit not null,
  note text,
  created_at timestamptz not null default now(),
  unique (from_ingredient_id, to_ingredient_id)
);

-- Indexes
create index if not exists ingredient_categories_display_order_idx on public.ingredient_categories (display_order);
create index if not exists ingredient_conversions_from_idx on public.ingredient_conversions (from_ingredient_id);
create index if not exists ingredient_conversions_to_idx on public.ingredient_conversions (to_ingredient_id);

-- Row Level Security (RLS)
alter table public.ingredient_categories enable row level security;
alter table public.ingredient_conversions enable row level security;

-- Policies: SELECT only for anon and authenticated
drop policy if exists "allow public read on ingredient_categories" on public.ingredient_categories;
create policy "allow public read on ingredient_categories" on public.ingredient_categories
  for select to anon, authenticated using (true);

drop policy if exists "allow public read on ingredient_conversions" on public.ingredient_conversions;
create policy "allow public read on ingredient_conversions" on public.ingredient_conversions
  for select to anon, authenticated using (true);

-- Permissions: Grant SELECT to anon and authenticated
grant select on public.ingredient_categories to anon, authenticated;
grant select on public.ingredient_conversions to anon, authenticated;

-- Revoke mutation rights
revoke insert, update, delete on public.ingredient_categories from anon, authenticated, public;
revoke insert, update, delete on public.ingredient_conversions from anon, authenticated, public;
