-- Migration: 202610260001_service_role_grants.sql
-- Description: Cấp toàn quyền cho service_role trên các bảng danh mục công khai để seed và bảo trì dữ liệu, giữ nguyên tắc anon/authenticated chỉ có quyền SELECT.

grant all on public.ingredient_categories to service_role;
grant all on public.ingredients to service_role;
grant all on public.ingredient_aliases to service_role;
grant all on public.recipes to service_role;
grant all on public.recipe_ingredients to service_role;
grant all on public.ingredient_conversions to service_role;
