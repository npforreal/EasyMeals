"""Test toàn diện các API công khai và tính toán không trạng thái của EasyMeals."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(repo):
    return TestClient(app)


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "easymeals"}


def test_manifest(client):
    res = client.get("/manifest.json")
    assert res.status_code == 200
    data = res.json()
    assert "EasyMeals" in data["name"]
    assert data["display"] == "standalone"


def test_html_pages(client):
    for path in ["/", "/planner", "/recipes", "/shopping-list", "/settings"]:
        res = client.get(path)
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]


def test_api_catalogue_and_etag(client, repo):
    res = client.get("/api/catalogue")
    assert res.status_code == 200
    data = res.json()
    assert "catalogue_version" in data
    assert "etag" in data
    assert len(data["ingredients"]) >= 20
    assert len(data["recipes"]) >= 4

    etag = res.headers.get("ETag")
    assert etag is not None

    # 1. ETag is stable across requests when data is unchanged
    res2 = client.get("/api/catalogue")
    assert res2.headers.get("ETag") == etag

    # 2. Test 304 Not Modified when If-None-Match matches
    res_cached = client.get("/api/catalogue", headers={"If-None-Match": etag})
    assert res_cached.status_code == 304

    # 3. Modify a recipe in the catalogue -> ETag must change
    first_recipe = next(iter(repo.recipes.values()))
    original_instructions = first_recipe.instructions
    first_recipe.instructions = "Hướng dẫn nấu mới cập nhật cho kiểm thử ETag"

    res_modified = client.get("/api/catalogue")
    assert res_modified.status_code == 200
    new_etag = res_modified.headers.get("ETag")
    assert new_etag is not None
    assert new_etag != etag, "ETag must change when catalogue data changes"

    # 4. Old If-None-Match returns 200 with new content
    res_stale = client.get("/api/catalogue", headers={"If-None-Match": etag})
    assert res_stale.status_code == 200
    assert res_stale.headers.get("ETag") == new_etag

    # Restore recipe
    first_recipe.instructions = original_instructions


def test_api_ingredients_search(client):
    res = client.get("/api/ingredients")
    assert res.status_code == 200
    all_ings = res.json()
    assert len(all_ings) >= 20

    res_search = client.get("/api/ingredients?q=băm")
    assert res_search.status_code == 200
    items = res_search.json()
    assert len(items) >= 1
    assert any("Thịt heo nạc dăm" in i["name"] for i in items)


def test_api_recipes(client):
    res = client.get("/api/recipes")
    assert res.status_code == 200
    recipes = res.json()
    assert len(recipes) >= 4

    res_man = client.get("/api/recipes?category=man")
    assert res_man.status_code == 200
    man_recipes = res_man.json()
    assert all(r["category"] == "man" for r in man_recipes)


def test_stateless_planner_generate_eat_and_undo_flow(client):
    # 1. Fetch available recipes
    res_rec = client.get("/api/recipes")
    recipes = res_rec.json()
    thit_kho_recipe = next(r for r in recipes if r["name"] == "Thịt kho tàu")
    recipe_id = thit_kho_recipe["id"]

    # Ingredients needed for Thịt kho tàu
    thit_ba_chi_id = thit_kho_recipe["ingredients"][0]["ingredient_id"]

    # 2. Call POST /api/planner/generate with pantry lots in payload
    pantry_input = [
        {
            "id": str(uuid4()),
            "ingredient_id": thit_ba_chi_id,
            "ingredient_name": "Thịt ba chỉ",
            "purchased_quantity": 1000,
            "remaining_quantity": 1000,
            "unit": "g",
            "purchased_at": "2026-10-24T08:00:00",
        }
    ]

    res_gen = client.post(
        "/api/planner/generate",
        json={
            "pantry": pantry_input,
            "start_date": "2026-10-25",
            "days": 3,
            "options": {"allow_leftovers": True},
        },
    )
    assert res_gen.status_code == 200
    gen_data = res_gen.json()
    assert gen_data["start_date"] == "2026-10-25"
    assert len(gen_data["meals"]) == 6  # 3 days x 2 meals (lunch, dinner)
    meal_plan_id = gen_data["meals"][0]["id"]

    # 3. Call POST /api/planner/eat (stateless FIFO stock deduction)
    eat_payload = {
        "pantry": pantry_input,
        "meal_plan_id": meal_plan_id,
        "dishes": [
            {
                "recipe_id": recipe_id,
                "is_leftover": False,
                "servings": 4,
            }
        ],
        "idempotency_key": "test_eat_key_001",
    }
    # Notice other ingredients of Thịt kho tàu (trứng vịt, hành tím) might be missing
    # -> Insufficient stock error returns 422 with deficits info
    res_eat = client.post("/api/planner/eat", json=eat_payload)
    assert res_eat.status_code == 422
    err_detail = res_eat.json()["detail"]
    assert "Không đủ nguyên liệu" in err_detail["message"]

    # Now add all required ingredients to pantry
    full_pantry = [
        {
            "id": str(uuid4()),
            "ingredient_id": ri["ingredient_id"],
            "ingredient_name": ri["ingredient_name"],
            "purchased_quantity": 1000,
            "remaining_quantity": 1000,
            "unit": ri["unit"],
            "purchased_at": "2026-10-24T08:00:00",
        }
        for ri in thit_kho_recipe["ingredients"]
    ]

    eat_payload["pantry"] = full_pantry
    res_eat_success = client.post("/api/planner/eat", json=eat_payload)
    assert res_eat_success.status_code == 200
    eat_result = res_eat_success.json()
    assert eat_result["success"] is True
    assert len(eat_result["movements"]) > 0

    # Verify updated lot remaining quantities
    updated_lots = eat_result["pantry"]
    thit_lot = next(lot for lot in updated_lots if lot["ingredient_id"] == thit_ba_chi_id)
    assert float(thit_lot["remaining_quantity"]) == 500.0  # 1000 - 500

    # 4. Call POST /api/planner/undo-eat
    undo_payload = {
        "pantry": updated_lots,
        "meal_plan_id": meal_plan_id,
        "movements": eat_result["movements"],
    }
    res_undo = client.post("/api/planner/undo-eat", json=undo_payload)
    assert res_undo.status_code == 200
    undo_result = res_undo.json()
    assert undo_result["success"] is True

    # Restored lot remaining quantity should be back to 1000
    restored_lots = undo_result["pantry"]
    thit_restored = next(lot for lot in restored_lots if lot["ingredient_id"] == thit_ba_chi_id)
    assert float(thit_restored["remaining_quantity"]) == 1000.0


def test_stateless_generate_converted_ingredient_shows_raw_name_and_ratio(
    client, repo, monkeypatch
):
    """A7 - Vòng 13: đường chạy API /generate phải truyền conversions + tên nguyên
    liệu gốc xuống engine; món dùng 'Cơm nguội' 500g với pantry rỗng phải gợi ý mua
    'Gạo' 200g (ratio 2.5), không phải 'Nguyên liệu gốc cho Cơm nguội' hay Cơm nguội."""
    all_recipes = repo.get_recipes()
    fried_rice = [r for r in all_recipes if r.name == "Cơm chiên Dương Châu lạp xưởng tôm"]
    assert fried_rice, "Catalogue phải còn món cơm chiên để test quy đổi gạo -> cơm."
    monkeypatch.setattr(repo, "get_recipes", lambda: fried_rice)

    res_gen = client.post(
        "/api/planner/generate",
        json={
            "pantry": [],
            "start_date": "2026-10-25",
            "days": 1,
            "options": {"allow_leftovers": False},
        },
    )
    assert res_gen.status_code == 200
    shopping = res_gen.json()["shopping_list"]
    gao_id = "0738fdf0-710e-5aed-bbb5-5ba1f0c05f3b"
    comnguoi_id = "16ddda98-781e-5ecf-9778-aedb4d1cd9ef"
    gao_items = [s for s in shopping if str(s["ingredient_id"]) == gao_id]
    assert gao_items, f"Danh sách mua phải quy đổi về 'Gạo', thực tế: {shopping}"
    item = gao_items[0]
    assert item["ingredient_name"] == "Gạo"
    assert float(item["needed_quantity"]) == 200.0
    assert item["unit"] == "g"
    assert all(str(s["ingredient_id"]) != comnguoi_id for s in shopping)


def test_stateless_regenerate_meal_and_recompute_shopping_api(client, repo):
    """B1, B2, B3, B4: Test API sinh lại 1 bữa và tính lại danh sách mua kèm ngân sách."""
    # 1. Sinh thực đơn 2 ngày
    res_gen = client.post(
        "/api/planner/generate",
        json={
            "pantry": [],
            "start_date": "2026-10-25",
            "days": 2,
            "options": {"allow_leftovers": False},
        },
    )
    assert res_gen.status_code == 200
    meals = res_gen.json()["meals"]
    target_meal = meals[0]

    # 2. Sinh lại bữa đầu tiên
    res_regen = client.post(
        "/api/planner/regenerate-meal",
        json={
            "target_meal_plan_id": target_meal["id"],
            "all_meal_plans": meals,
            "pantry": [],
            "options": {"allow_leftovers": False},
        },
    )
    assert res_regen.status_code == 200
    regen_data = res_regen.json()
    assert regen_data["success"] is True
    assert regen_data["meal"]["id"] == target_meal["id"]
    assert len(regen_data["meal"]["dishes"]) > 0

    # 3. Thử sinh lại bữa đã ăn -> 400 Bad Request
    target_meal_eaten = dict(target_meal)
    target_meal_eaten["eaten_at"] = "2026-10-25T12:00:00"
    meals_with_eaten = [target_meal_eaten] + meals[1:]
    res_regen_eaten = client.post(
        "/api/planner/regenerate-meal",
        json={
            "target_meal_plan_id": target_meal["id"],
            "all_meal_plans": meals_with_eaten,
            "pantry": [],
        },
    )
    assert res_regen_eaten.status_code == 400
    assert "đã được đánh dấu ăn" in res_regen_eaten.json()["detail"]

    # 4. Tính lại danh sách mua từ các bữa
    res_recompute = client.post(
        "/api/planner/recompute-shopping",
        json={
            "meal_plans": meals,
            "pantry": [],
        },
    )
    assert res_recompute.status_code == 200
    recomp_data = res_recompute.json()
    assert len(recomp_data["shopping_list"]) > 0
    assert "total_estimated_budget" in recomp_data
    assert "total_spent" in recomp_data
