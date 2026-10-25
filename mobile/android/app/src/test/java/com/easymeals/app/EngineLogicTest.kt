package com.easymeals.app

import com.easymeals.app.domain.engine.*
import com.easymeals.app.domain.model.*
import com.easymeals.app.ui.theme.GeneratedTokens
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.io.InputStreamReader

class EngineLogicTest {

    private lateinit var fixtureJson: JSONObject
    private val gson = Gson()

    @Before
    fun setUp() {
        val inputStream = javaClass.classLoader?.getResourceAsStream("engine_logic_cases.json")
            ?: throw IllegalStateException("Không tìm thấy engine_logic_cases.json trong test resources")
        val jsonText = InputStreamReader(inputStream).readText()
        fixtureJson = JSONObject(jsonText)
    }

    private fun norm(v: String): String {
        return ExactDecimal(v).toString()
    }

    private fun toRecipe(obj: JSONObject): Recipe {
        val ingredientsArray = obj.getJSONArray("ingredients")
        val ingredients = mutableListOf<RecipeIngredient>()
        for (i in 0 until ingredientsArray.length()) {
            val ing = ingredientsArray.getJSONObject(i)
            val name = if (ing.has("name")) ing.getString("name") else ing.optString("ingredient_name", "")
            ingredients.add(
                RecipeIngredient(
                    ingredientId = ing.getString("ingredient_id"),
                    ingredientName = name,
                    quantity = ing.getString("quantity"),
                    unit = ing.getString("unit")
                )
            )
        }
        return Recipe(
            id = obj.getString("id"),
            name = obj.getString("name"),
            category = obj.getString("category"),
            servings = obj.optInt("servings", 4),
            ingredients = ingredients
        )
    }

    private fun toLots(arr: JSONArray): List<PantryLot> {
        val lots = mutableListOf<PantryLot>()
        for (i in 0 until arr.length()) {
            val item = arr.getJSONObject(i)
            val name = if (item.has("name")) item.getString("name") else item.optString("ingredient_name", "")
            val purchased = if (item.has("purchased")) item.getString("purchased") else item.optString("purchased_quantity", "0")
            val remaining = if (item.has("remaining")) item.getString("remaining") else item.optString("remaining_quantity", "0")
            val expiresAt = if (item.isNull("expires_at")) null else item.optString("expires_at", null)
            lots.add(
                PantryLot(
                    id = item.getString("id"),
                    ingredientId = item.getString("ingredient_id"),
                    ingredientName = name,
                    purchasedQuantity = purchased,
                    remainingQuantity = remaining,
                    unit = item.getString("unit"),
                    purchasedAt = "2025-12-01T00:00:00",
                    expiresAt = expiresAt
                )
            )
        }
        return lots
    }

    @Test
    fun testAllLogicCases() {
        val cases = fixtureJson.getJSONArray("cases")
        for (i in 0 until cases.length()) {
            val c = cases.getJSONObject(i)
            val name = c.getString("name")
            val op = c.getString("op")

            val convsType = object : TypeToken<List<Conversion>>() {}.type
            val convs: List<Conversion>? = if (c.has("conversions")) {
                gson.fromJson(c.getJSONArray("conversions").toString(), convsType)
            } else null

            val multiplier = if (c.has("multiplier")) c.getString("multiplier") else "1"

            when (op) {
                "check" -> {
                    val recipe = toRecipe(c.getJSONObject("recipe"))
                    val pantry = toLots(c.getJSONArray("pantry"))

                    val (canCook, deficits) = EasyMealsEngine.checkRecipeStock(recipe, pantry, multiplier, convs)
                    val exp = c.getJSONObject("expect")
                    assertEquals("[$name] can_cook", exp.getBoolean("can_cook"), canCook)

                    val expDeficits = exp.getJSONObject("deficits")
                    assertEquals("[$name] deficits count", expDeficits.length(), deficits.size)
                    for (key in expDeficits.keys()) {
                        assertTrue("[$name] missing deficit for $key", deficits.containsKey(key))
                        assertEquals("[$name] deficit amount for $key", norm(expDeficits.getString(key)), norm(deficits[key]!!.missingQuantity))
                    }
                }
                "fifo" -> {
                    val recipe = toRecipe(c.getJSONObject("recipe"))
                    val pantry = toLots(c.getJSONArray("pantry"))

                    val (updatedLots, movements) = EasyMealsEngine.deductRecipeStockFifo(
                        pantry, recipe, "plan-1", "key", multiplier, convs
                    )
                    assertTrue("[$name] movements should not be empty", movements.isNotEmpty())

                    val expRemaining = c.getJSONObject("expect").getJSONObject("remaining")
                    val actualRemaining = pantry.associate { it.id to norm(it.remainingQuantity) }.toMutableMap()
                    for (u in updatedLots) {
                        actualRemaining[u.id] = norm(u.remainingQuantity)
                    }

                    for (key in expRemaining.keys()) {
                        assertEquals("[$name] lot $key remaining", norm(expRemaining.getString(key)), actualRemaining[key])
                    }
                }
                "deduct_available" -> {
                    val recipe = toRecipe(c.getJSONObject("recipe"))
                    val pantry = toLots(c.getJSONArray("pantry"))

                    val outcome = EasyMealsEngine.deductRecipeStockAvailable(
                        pantry, recipe, "plan-1", "key", multiplier, convs
                    )

                    val exp = c.getJSONObject("expect")
                    val expRemaining = exp.getJSONObject("remaining")
                    val actualRemaining = pantry.associate { it.id to norm(it.remainingQuantity) }.toMutableMap()
                    for (u in outcome.updatedLots) {
                        actualRemaining[u.id] = norm(u.remainingQuantity)
                    }
                    for (key in expRemaining.keys()) {
                        assertEquals("[$name] lot $key remaining", norm(expRemaining.getString(key)), actualRemaining[key])
                    }

                    val expDeficits = exp.getJSONObject("deficits")
                    assertEquals("[$name] deficits count", expDeficits.length(), outcome.deficits.size)
                    for (key in expDeficits.keys()) {
                        assertTrue("[$name] missing deficit for $key", outcome.deficits.containsKey(key))
                        assertEquals("[$name] deficit amount for $key", norm(expDeficits.getString(key)), norm(outcome.deficits[key]!!.missingQuantity))
                    }

                    val expMovements = exp.getJSONObject("movements")
                    val actualMovements = outcome.movements.associate { it.pantryLotId to norm(it.quantityDelta) }
                    for (key in expMovements.keys()) {
                        assertEquals("[$name] movement for $key", norm(expMovements.getString(key)), actualMovements[key])
                    }
                }
                "undo" -> {
                    val pantry = toLots(c.getJSONArray("pantry"))

                    val movementsJson = c.getJSONArray("movements")
                    val movements = mutableListOf<StockMovement>()
                    for (j in 0 until movementsJson.length()) {
                        val m = movementsJson.getJSONObject(j)
                        movements.add(
                            StockMovement(
                                id = m.getString("id"),
                                pantryLotId = m.getString("pantry_lot_id"),
                                quantityDelta = m.getString("delta"),
                                reason = m.getString("reason"),
                                mealPlanId = m.getString("meal_plan_id"),
                                idempotencyKey = m.getString("idempotency_key")
                            )
                        )
                    }

                    val (restoredLots, _) = EasyMealsEngine.reverseStockMovements(
                        pantry, movements, c.getString("meal_plan_id")
                    )

                    val expRemaining = c.getJSONObject("expect").getJSONObject("remaining")
                    val actualRemaining = pantry.associate { it.id to norm(it.remainingQuantity) }.toMutableMap()
                    for (u in restoredLots) {
                        actualRemaining[u.id] = norm(u.remainingQuantity)
                    }
                    for (key in expRemaining.keys()) {
                        assertEquals("[$name] lot $key remaining", norm(expRemaining.getString(key)), actualRemaining[key])
                    }
                }
                "merge_plans" -> {
                    val planListType = object : TypeToken<List<MealPlan>>() {}.type
                    val existing: List<MealPlan> = gson.fromJson(
                        c.getJSONArray("existing").toString(), planListType
                    )
                    val newPlans: List<MealPlan> = gson.fromJson(
                        c.getJSONArray("new_plans").toString(), planListType
                    )
                    val merged = EasyMealsEngine.mergeNewPlansIntoExisting(
                        existing, newPlans, if (c.has("mode")) c.getString("mode") else "replace"
                    )
                    val expKept = c.getJSONObject("expect").getJSONArray("kept_ids")
                    assertEquals("[$name] kept ids", expKept.length(), merged.size)
                    for (k in 0 until expKept.length()) {
                        assertEquals("[$name] kept $k", expKept.getString(k), merged[k].id)
                    }
                }
                "plan" -> {
                    val recipesArray = c.getJSONArray("recipes")
                    val recipes = mutableListOf<Recipe>()
                    for (j in 0 until recipesArray.length()) {
                        recipes.add(toRecipe(recipesArray.getJSONObject(j)))
                    }
                    val pantry = toLots(c.getJSONArray("pantry"))

                    val start = java.time.LocalDate.parse(c.getString("start"))
                    val end = start.plusDays(c.getLong("days") - 1)
                    val allowLeftovers = c.optBoolean("allow_leftovers", true)
                    val leftoverDays = c.optInt("leftover_days", GeneratedTokens.PlanLimits.LEFTOVER_DEFAULT_DAYS)

                    val exp = c.getJSONObject("expect")
                    if (exp.optBoolean("error", false)) {
                        try {
                            EasyMealsEngine.generatePeriodPlan(
                                startDateStr = start.toString(),
                                endDateStr = end.toString(),
                                recipes = recipes,
                                currentPantryLots = pantry,
                                allowLeftovers = allowLeftovers,
                                conversions = convs,
                                leftoverDays = leftoverDays
                            )
                            org.junit.Assert.fail("[$name] Mong đợi IncompatibleUnitException nhưng không ném")
                        } catch (_: IncompatibleUnitException) {
                            // Passed
                        } catch (_: IllegalArgumentException) {
                            // Passed
                        }
                        continue
                    }

                    val (_, plans, shopping) = EasyMealsEngine.generatePeriodPlan(
                        startDateStr = start.toString(),
                        endDateStr = end.toString(),
                        recipes = recipes,
                        currentPantryLots = pantry,
                        allowLeftovers = allowLeftovers,
                        conversions = convs,
                        leftoverDays = leftoverDays
                    )

                    val expDishes = exp.getJSONArray("dishes")
                    val actualDishes = plans.flatMap { it.dishes }.map { it.recipeName }
                    assertEquals("[$name] dishes count", expDishes.length(), actualDishes.size)
                    for (k in 0 until expDishes.length()) {
                        assertEquals("[$name] dish $k", expDishes.getString(k), actualDishes[k])
                    }

                    val expShopping = exp.getJSONObject("shopping")
                    assertEquals("[$name] shopping count", expShopping.length(), shopping.size)
                    for (key in expShopping.keys()) {
                        val expItem = expShopping.getJSONArray(key)
                        val actualItem = shopping.firstOrNull { it.ingredientId == key }
                        assertNotNull("[$name] shopping item $key missing", actualItem)
                        assertEquals("[$name] shopping qty for $key", norm(expItem.getString(0)), norm(actualItem!!.neededQuantity))
                        assertEquals("[$name] shopping unit for $key", expItem.getString(1), actualItem.unit)
                    }
                }
            }
        }
    }
}
