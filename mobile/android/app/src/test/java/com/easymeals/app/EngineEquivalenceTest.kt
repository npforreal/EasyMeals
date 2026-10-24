package com.easymeals.app

import com.easymeals.app.domain.engine.*
import com.easymeals.app.domain.model.*
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.io.InputStreamReader

class EngineEquivalenceTest {

    private lateinit var fixtureJson: JSONObject
    private val gson = Gson()

    @Before
    fun setUp() {
        val inputStream = javaClass.classLoader?.getResourceAsStream("engine_test_cases.json")
            ?: throw IllegalStateException("Không tìm thấy engine_test_cases.json trong test resources")
        val jsonText = InputStreamReader(inputStream).readText()
        fixtureJson = JSONObject(jsonText)
    }

    @Test
    fun testUnitConversions() {
        val items = fixtureJson.getJSONArray("unit_conversions")
        for (i in 0 until items.length()) {
            val item = items.getJSONObject(i)
            val qty = item.getString("quantity")
            val fromUnit = item.getString("from_unit")
            val toUnit = item.getString("to_unit")
            val expected = item.getString("expected")

            val res = UnitDimensions.convert(ExactDecimal(qty), fromUnit, toUnit)
            assertEquals("Chuyển đổi $qty $fromUnit -> $toUnit phải bằng $expected", expected, res.toString())
        }
    }

    @Test
    fun testFifoStockDeduction() {
        val fifoDict = fixtureJson.getJSONObject("fifo_deduction")
        val recipe = gson.fromJson(fifoDict.getJSONObject("recipe").toString(), Recipe::class.java)
        val pantryLotsType = object : TypeToken<List<PantryLot>>() {}.type
        val pantryLots: List<PantryLot> = gson.fromJson(fifoDict.getJSONArray("pantry").toString(), pantryLotsType)

        val (canCook, deficits) = EasyMealsEngine.checkRecipeStock(recipe, pantryLots)
        val checkExp = fifoDict.getJSONObject("check_stock_expected")
        assertEquals(checkExp.getBoolean("can_cook"), canCook)
        assertEquals(checkExp.getInt("deficits_count"), deficits.size)

        val (updatedLots, movements) = EasyMealsEngine.deductRecipeStockFifo(
            pantryLots,
            recipe,
            "bbbbbbbb-0001-0000-0000-000000000001",
            "fifo_test"
        )

        val dedExp = fifoDict.getJSONObject("deduction_expected")
        val expLots = dedExp.getJSONArray("updated_lots")
        assertEquals(expLots.length(), updatedLots.size)

        for (i in 0 until updatedLots.size) {
            val exp = expLots.getJSONObject(i)
            assertEquals(exp.getString("id"), updatedLots[i].id)
            assertEquals(exp.getString("remaining_quantity"), updatedLots[i].remainingQuantity)
        }

        val expMovs = dedExp.getJSONArray("movements")
        assertEquals(expMovs.length(), movements.size)
        for (i in 0 until movements.size) {
            val exp = expMovs.getJSONObject(i)
            assertEquals(exp.getString("pantry_lot_id"), movements[i].pantryLotId)
            assertEquals(exp.getString("quantity_delta"), movements[i].quantityDelta)
            assertEquals(exp.getString("reason"), movements[i].reason)
        }
    }

    @Test
    fun testUndoConsumption() {
        val fifoDict = fixtureJson.getJSONObject("fifo_deduction")
        val undoDict = fixtureJson.getJSONObject("undo_consumption")

        val recipe = gson.fromJson(fifoDict.getJSONObject("recipe").toString(), Recipe::class.java)
        val pantryLotsType = object : TypeToken<List<PantryLot>>() {}.type
        val pantryLots: List<PantryLot> = gson.fromJson(fifoDict.getJSONArray("pantry").toString(), pantryLotsType)

        val (updatedLots, movements) = EasyMealsEngine.deductRecipeStockFifo(
            pantryLots,
            recipe,
            "bbbbbbbb-0001-0000-0000-000000000001",
            "fifo_test"
        )

        val (restoredLots, _) = EasyMealsEngine.reverseStockMovements(
            updatedLots,
            movements,
            "bbbbbbbb-0001-0000-0000-000000000001"
        )

        val expRestored = undoDict.getJSONArray("restored_lots")
        assertEquals(expRestored.length(), restoredLots.size)
        for (i in 0 until restoredLots.size) {
            val exp = expRestored.getJSONObject(i)
            assertEquals(exp.getString("id"), restoredLots[i].id)
            assertEquals(exp.getString("remaining_quantity"), restoredLots[i].remainingQuantity)
        }
    }

    @Test
    fun testMealPlannerGeneration() {
        val planData = fixtureJson.getJSONObject("planner_generation")
        val recipesType = object : TypeToken<List<Recipe>>() {}.type
        val recipes: List<Recipe> = gson.fromJson(planData.getJSONArray("recipes").toString(), recipesType)

        val pantryType = object : TypeToken<List<PantryLot>>() {}.type
        val pantryLots: List<PantryLot> = gson.fromJson(planData.getJSONArray("pantry").toString(), pantryType)

        val startDate = planData.getString("start_date")
        val endDate = planData.getString("end_date")

        val (_, meals, shoppingList) = EasyMealsEngine.generatePeriodPlan(
            startDate,
            endDate,
            recipes,
            pantryLots,
            allowLeftovers = true
        )

        assertEquals(planData.getInt("expected_meals_count"), meals.size)

        val expDishesPerMeal = planData.getJSONArray("expected_dishes_per_meal")
        for (m in 0 until meals.size) {
            val actualDishes = meals[m].dishes
            val expDishes = expDishesPerMeal.getJSONArray(m)
            assertEquals(expDishes.length(), actualDishes.size)

            for (d in 0 until actualDishes.size) {
                val exp = expDishes.getJSONObject(d)
                assertEquals(exp.getString("recipe_name"), actualDishes[d].recipeName)
                assertEquals(exp.getString("category"), actualDishes[d].category)
                assertEquals(exp.getBoolean("is_leftover"), actualDishes[d].isLeftover)
            }
        }

        val sortedActual = shoppingList.sortedBy { it.ingredientId }
        val expShopping = planData.getJSONArray("expected_shopping_items")
        assertEquals(expShopping.length(), sortedActual.size)

        for (s in 0 until sortedActual.size) {
            val exp = expShopping.getJSONObject(s)
            assertEquals(exp.getString("ingredient_id"), sortedActual[s].ingredientId)
            assertEquals(exp.getString("needed_quantity"), sortedActual[s].neededQuantity)
            assertEquals(exp.getString("unit"), sortedActual[s].unit)
        }
    }

    @Test
    fun testFifoSameExpiryTiebreak() {
        val tieData = fixtureJson.getJSONObject("fifo_deduction_same_expiry_tiebreak")
        val recipe = gson.fromJson(tieData.getJSONObject("recipe").toString(), Recipe::class.java)
        val pantryType = object : TypeToken<List<PantryLot>>() {}.type
        val pantryLots: List<PantryLot> = gson.fromJson(tieData.getJSONArray("pantry").toString(), pantryType)

        val (canCook, deficits) = EasyMealsEngine.checkRecipeStock(recipe, pantryLots)
        val checkExp = tieData.getJSONObject("check_stock_expected")
        assertEquals(checkExp.getBoolean("can_cook"), canCook)
        assertEquals(checkExp.getInt("deficits_count"), deficits.size)

        val (updatedLots, movements) = EasyMealsEngine.deductRecipeStockFifo(
            pantryLots,
            recipe,
            "bbbbbbbb-0001-0000-000000000010",
            "tiebreak_test"
        )

        val expLots = tieData.getJSONObject("deduction_expected").getJSONArray("updated_lots")
        assertEquals(expLots.length(), updatedLots.size)
        assertEquals(expLots.getJSONObject(0).getString("id"), updatedLots[0].id)
        assertEquals(expLots.getJSONObject(0).getString("remaining_quantity"), updatedLots[0].remainingQuantity)
        assertEquals(expLots.getJSONObject(1).getString("id"), updatedLots[1].id)
        assertEquals(expLots.getJSONObject(1).getString("remaining_quantity"), updatedLots[1].remainingQuantity)

        val expMovs = tieData.getJSONObject("deduction_expected").getJSONArray("movements")
        assertEquals(expMovs.length(), movements.size)
        for (i in 0 until movements.size) {
            val exp = expMovs.getJSONObject(i)
            assertEquals(exp.getString("pantry_lot_id"), movements[i].pantryLotId)
            assertEquals(exp.getString("quantity_delta"), movements[i].quantityDelta)
            assertEquals(exp.getString("reason"), movements[i].reason)
        }
    }

    @Test(expected = InsufficientStockException::class)
    fun testStockInsufficient() {
        val insuff = fixtureJson.getJSONObject("stock_insufficient")
        val recipe = gson.fromJson(insuff.getJSONObject("recipe").toString(), Recipe::class.java)
        val pantryType = object : TypeToken<List<PantryLot>>() {}.type
        val pantryLots: List<PantryLot> = gson.fromJson(insuff.getJSONArray("pantry").toString(), pantryType)

        val (canCook, deficits) = EasyMealsEngine.checkRecipeStock(recipe, pantryLots)
        val checkExp = insuff.getJSONObject("check_stock_expected")
        assertEquals(checkExp.getBoolean("can_cook"), canCook)
        assertEquals(checkExp.getInt("deficits_count"), deficits.size)

        EasyMealsEngine.deductRecipeStockFifo(
            pantryLots,
            recipe,
            "bbbbbbbb-0001-0000-000000000011",
            "insuff_test"
        )
    }

    @Test(expected = IncompatibleUnitException::class)
    fun testUnitConversionIncompatibleMassVolume() {
        val incompat = fixtureJson.getJSONObject("unit_conversion_incompatible_mass_volume")
        val exp = incompat.getJSONObject("conversion_expected")
        UnitDimensions.convert(ExactDecimal(exp.getString("quantity")), exp.getString("from_unit"), exp.getString("to_unit"))
    }
}
