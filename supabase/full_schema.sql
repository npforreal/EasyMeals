-- EasyMeals Baseline Schema: Public Shared Catalogue Only
-- This schema contains ONLY shared culinary data: ingredients, aliases, recipes, recipe_ingredients.
-- Personal data (pantry, plans, stock movements) is stored exclusively on the client (IndexedDB).

create extension if not exists pgcrypto;

-- Enums
create type public.dish_category as enum ('man', 'rau', 'canh');
create type public.quantity_unit as enum ('g', 'kg', 'ml', 'l', 'piece');

-- 1. Ingredients
create table public.ingredients (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  normalized_name text not null unique,
  category text,
  created_at timestamptz not null default now()
);

-- 2. Ingredient Aliases
create table public.ingredient_aliases (
  id uuid primary key default gen_random_uuid(),
  ingredient_id uuid not null references public.ingredients(id) on delete cascade,
  alias text not null,
  normalized_alias text not null unique
);

-- 3. Recipes
create table public.recipes (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  category public.dish_category not null,
  instructions jsonb not null default '[]'::jsonb,
  servings integer not null default 1 check (servings > 0),
  created_at timestamptz not null default now()
);

-- 4. Recipe Ingredients
create table public.recipe_ingredients (
  recipe_id uuid not null references public.recipes(id) on delete cascade,
  ingredient_id uuid not null references public.ingredients(id),
  quantity numeric(12,3) not null check (quantity > 0),
  unit public.quantity_unit not null,
  primary key (recipe_id, ingredient_id)
);

-- Indexes for efficient querying & text search
create index ingredients_normalized_name_idx on public.ingredients (normalized_name);
create index ingredients_category_idx on public.ingredients (category);
create index ingredient_aliases_normalized_idx on public.ingredient_aliases (normalized_alias);
create index ingredient_aliases_ingredient_id_idx on public.ingredient_aliases (ingredient_id);
create index recipes_category_idx on public.recipes (category);
create index recipe_ingredients_ingredient_idx on public.recipe_ingredients (ingredient_id);
create index recipe_ingredients_recipe_idx on public.recipe_ingredients (recipe_id);

-- Row Level Security (RLS): Read-only for anon and authenticated
alter table public.ingredients enable row level security;
alter table public.ingredient_aliases enable row level security;
alter table public.recipes enable row level security;
alter table public.recipe_ingredients enable row level security;

-- Policies: Only SELECT is permitted
create policy "allow public read on ingredients" on public.ingredients
  for select to anon, authenticated using (true);

create policy "allow public read on ingredient_aliases" on public.ingredient_aliases
  for select to anon, authenticated using (true);

create policy "allow public read on recipes" on public.recipes
  for select to anon, authenticated using (true);

create policy "allow public read on recipe_ingredients" on public.recipe_ingredients
  for select to anon, authenticated using (true);

-- Permissions: Grant SELECT to anon and authenticated
grant select on public.ingredients to anon, authenticated;
grant select on public.ingredient_aliases to anon, authenticated;
grant select on public.recipes to anon, authenticated;
grant select on public.recipe_ingredients to anon, authenticated;

-- Revoke all mutation rights from web roles
revoke insert, update, delete on public.ingredients from anon, authenticated, public;
revoke insert, update, delete on public.ingredient_aliases from anon, authenticated, public;
revoke insert, update, delete on public.recipes from anon, authenticated, public;
revoke insert, update, delete on public.recipe_ingredients from anon, authenticated, public;
