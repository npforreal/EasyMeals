-- Vòng 13 / Giai đoạn E: metadata thời gian nấu, độ khó và mẹo bảo quản công thức.
alter table public.recipes
  add column if not exists prep_time_minutes integer,
  add column if not exists prep_time_source_url text,
  add column if not exists prep_time_verified_at date,
  add column if not exists cook_time_minutes integer,
  add column if not exists cook_time_source_url text,
  add column if not exists cook_time_verified_at date,
  add column if not exists difficulty text check (difficulty is null or difficulty in ('easy', 'medium', 'hard')),
  add column if not exists difficulty_source_url text,
  add column if not exists difficulty_verified_at date,
  add column if not exists storage_tips text[] not null default '{}'::text[],
  add column if not exists storage_source_url text,
  add column if not exists storage_verified_at date;

grant select on public.recipes to anon, authenticated;
revoke insert, update, delete on public.recipes from anon, authenticated, public;
grant all on public.recipes to service_role;
