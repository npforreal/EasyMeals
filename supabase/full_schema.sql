-- EasyMeals Baseline Schema: Public Shared Catalogue Only
-- This schema contains ONLY shared culinary data: ingredients, aliases, recipes, recipe_ingredients, ingredient_categories, ingredient_conversions.
-- Personal data (pantry, plans, stock movements) is stored exclusively on the client (IndexedDB).

create extension if not exists pgcrypto;

-- Enums
create type public.dish_category as enum ('man', 'rau', 'canh');
create type public.quantity_unit as enum ('g', 'kg', 'ml', 'l', 'piece');

-- 1. Ingredient Categories
create table public.ingredient_categories (
  id text primary key,
  name text not null,
  name_vi text not null,
  display_order integer not null default 0,
  created_at timestamptz not null default now()
);

-- 2. Ingredients
create table public.ingredients (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  normalized_name text not null unique,
  category text check (category in ('thit', 'gia_cam', 'hai_san', 'trung_sua', 'rau_cu', 'cu_qua', 'gao_bot_mi', 'gia_vi', 'nuoc_cham_dau', 'khac')),
  default_unit public.quantity_unit not null default 'g',
  created_at timestamptz not null default now()
);

-- 3. Ingredient Aliases
create table public.ingredient_aliases (
  id uuid primary key default gen_random_uuid(),
  ingredient_id uuid not null references public.ingredients(id) on delete cascade,
  alias text not null,
  normalized_alias text not null unique
);

-- 4. Recipes
create table public.recipes (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  category public.dish_category not null,
  instructions jsonb not null default '[]'::jsonb,
  servings integer not null default 1 check (servings > 0),
  created_at timestamptz not null default now()
);

-- 5. Recipe Ingredients
create table public.recipe_ingredients (
  recipe_id uuid not null references public.recipes(id) on delete cascade,
  ingredient_id uuid not null references public.ingredients(id),
  quantity numeric(12,3) not null check (quantity > 0),
  unit public.quantity_unit not null,
  primary key (recipe_id, ingredient_id)
);

-- 6. Ingredient Conversions
create table public.ingredient_conversions (
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

-- Indexes for efficient querying & text search
create index ingredient_categories_display_order_idx on public.ingredient_categories (display_order);
create index ingredients_normalized_name_idx on public.ingredients (normalized_name);
create index ingredients_category_idx on public.ingredients (category);
create index ingredient_aliases_normalized_idx on public.ingredient_aliases (normalized_alias);
create index ingredient_aliases_ingredient_id_idx on public.ingredient_aliases (ingredient_id);
create index recipes_category_idx on public.recipes (category);
create index recipe_ingredients_ingredient_idx on public.recipe_ingredients (ingredient_id);
create index recipe_ingredients_recipe_idx on public.recipe_ingredients (recipe_id);
create index ingredient_conversions_from_idx on public.ingredient_conversions (from_ingredient_id);
create index ingredient_conversions_to_idx on public.ingredient_conversions (to_ingredient_id);

-- Row Level Security (RLS): Read-only for anon and authenticated
alter table public.ingredient_categories enable row level security;
alter table public.ingredients enable row level security;
alter table public.ingredient_aliases enable row level security;
alter table public.recipes enable row level security;
alter table public.recipe_ingredients enable row level security;
alter table public.ingredient_conversions enable row level security;

-- Policies: Only SELECT is permitted
create policy "allow public read on ingredient_categories" on public.ingredient_categories
  for select to anon, authenticated using (true);

create policy "allow public read on ingredients" on public.ingredients
  for select to anon, authenticated using (true);

create policy "allow public read on ingredient_aliases" on public.ingredient_aliases
  for select to anon, authenticated using (true);

create policy "allow public read on recipes" on public.recipes
  for select to anon, authenticated using (true);

create policy "allow public read on recipe_ingredients" on public.recipe_ingredients
  for select to anon, authenticated using (true);

create policy "allow public read on ingredient_conversions" on public.ingredient_conversions
  for select to anon, authenticated using (true);

-- Permissions: Grant SELECT to anon and authenticated
grant select on public.ingredient_categories to anon, authenticated;
grant select on public.ingredients to anon, authenticated;
grant select on public.ingredient_aliases to anon, authenticated;
grant select on public.recipes to anon, authenticated;
grant select on public.recipe_ingredients to anon, authenticated;
grant select on public.ingredient_conversions to anon, authenticated;

-- Revoke all mutation rights from web roles
revoke insert, update, delete on public.ingredient_categories from anon, authenticated, public;
revoke insert, update, delete on public.ingredients from anon, authenticated, public;
revoke insert, update, delete on public.ingredient_aliases from anon, authenticated, public;
revoke insert, update, delete on public.recipes from anon, authenticated, public;
revoke insert, update, delete on public.recipe_ingredients from anon, authenticated, public;
revoke insert, update, delete on public.ingredient_conversions from anon, authenticated, public;

-- Grant administrative rights to service_role for catalogue seeding
grant all on public.ingredient_categories to service_role;
grant all on public.ingredients to service_role;
grant all on public.ingredient_aliases to service_role;
grant all on public.recipes to service_role;
grant all on public.recipe_ingredients to service_role;
grant all on public.ingredient_conversions to service_role;

-- Vòng 13 / Giai đoạn D: metadata có căn cứ (rows cũ giữ trạng thái unknown).
alter table public.ingredients
  add column allergens text[] not null default '{}'::text[],
  add column allergen_verification_status text not null default 'unknown'
    check (allergen_verification_status in ('unknown', 'incomplete', 'verified')),
  add column allergen_source_url text,
  add column allergen_verified_at date,
  add constraint ingredients_allergen_evidence_check check (
    allergen_verification_status <> 'verified'
    or (allergen_source_url is not null and allergen_verified_at is not null)
  ),
  add constraint ingredients_allergen_source_pair_check check (
    (allergen_source_url is null) = (allergen_verified_at is null)
  ),
  add constraint ingredients_unknown_allergens_empty_check check (
    allergen_verification_status <> 'unknown' or cardinality(allergens) = 0
  );

alter table public.recipes
  add column dietary_status text not null default 'unknown'
    check (dietary_status in ('unknown', 'incomplete', 'omnivore', 'vegetarian', 'vegan')),
  add column dietary_source_url text,
  add column dietary_verified_at date,
  add column spice_level smallint check (spice_level between 0 and 5),
  add column spice_source_url text,
  add column spice_verified_at date,
  add constraint recipes_dietary_evidence_check check (
    dietary_status not in ('omnivore', 'vegetarian', 'vegan')
    or (dietary_source_url is not null and dietary_verified_at is not null)
  ),
  add constraint recipes_dietary_source_pair_check check (
    (dietary_source_url is null) = (dietary_verified_at is null)
  ),
  add constraint recipes_spice_evidence_check check (
    (spice_level is null and spice_source_url is null and spice_verified_at is null)
    or (spice_level is not null and spice_source_url is not null and spice_verified_at is not null)
  ),
  add column prep_time_minutes integer,
  add column prep_time_source_url text,
  add column prep_time_verified_at date,
  add column cook_time_minutes integer,
  add column cook_time_source_url text,
  add column cook_time_verified_at date,
  add column difficulty text check (difficulty is null or difficulty in ('easy', 'medium', 'hard')),
  add column difficulty_source_url text,
  add column difficulty_verified_at date,
  add column storage_tips text[] not null default '{}'::text[],
  add column storage_source_url text,
  add column storage_verified_at date;

grant select on public.ingredients, public.recipes to anon, authenticated;
revoke insert, update, delete on public.ingredients, public.recipes from anon, authenticated, public;
