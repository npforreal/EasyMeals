-- Vòng 13 / Giai đoạn D: evidence-backed shared catalogue metadata.
-- Existing rows deliberately remain unknown; no allergen/dietary facts are inferred.
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
  );

-- Preserve public read-only catalogue access. Both grants and RLS are required.
grant select on public.ingredients, public.recipes to anon, authenticated;
revoke insert, update, delete on public.ingredients, public.recipes from anon, authenticated, public;
