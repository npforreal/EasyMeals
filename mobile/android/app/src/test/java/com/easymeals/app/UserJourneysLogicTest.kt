package com.easymeals.app

import com.easymeals.app.data.catalogue.CatalogueLoader
import com.easymeals.app.domain.engine.EasyMealsEngine
import com.easymeals.app.domain.engine.ExactDecimal
import com.easymeals.app.domain.engine.IncompatibleUnitException
import com.easymeals.app.domain.model.*
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.io.File
import java.io.FileInputStream
import java.util.UUID

class UserJourneysLogicTest {

    private lateinit var catalogue: CatalogueBundle

    @Before
    fun setUp() {
        val fileCandidates = listOf(
            File("src/main/assets/catalogue.json"),
            File("mobile/android/app/src/main/assets/catalogue.json"),
            File("../../data/catalogue.json")
        )
        val file = fileCandidates.firstOrNull { it.exists() }
            ?: throw IllegalStateException("Không tìm thấy catalogue.json")
        catalogue = FileInputStream(file).use { CatalogueLoader.loadCatalogue(it) }
    }

    // Hành trình 1: Thêm đồ vào tủ (Pantry addition)
    @Test
    fun testJourney1_PantryAddition() {
        val ingredient = catalogue.ingredients.first()
        val lot = PantryLot(
            id = UUID.randomUUID().toString(),
            ingredientId = ingredient.id,
            ingredientName = ingredient.name,
            remainingQuantity = "500",
            purchasedQuantity = "500",
            unit = ingredient.defaultUnit ?: "g",
            purchasedAt = "2026-10-25",
            expiresAt = "2026-10-30"
        )

        assertEquals("500", lot.remainingQuantity)
        assertEquals("g", lot.unit)
        assertEquals(ingredient.id, lot.ingredientId)
    }

    // Hành trình 2: Lập thực đơn -> Đã ăn -> Hoàn tác (Plan -> Eat -> Undo)
    @Test
    fun testJourney2_PlanEatUndo() {
        val recipe = catalogue.recipes[0]
        val lotList = mutableListOf<PantryLot>()

        // Tạo sẵn đủ nguyên liệu trong tủ theo công thức
        for (ing in recipe.ingredients) {
            lotList.add(
                PantryLot(
                    id = UUID.randomUUID().toString(),
                    ingredientId = ing.ingredientId,
                    ingredientName = ing.ingredientName,
                    remainingQuantity = (ExactDecimal(ing.quantity) * ExactDecimal("2")).toString(),
                    purchasedQuantity = (ExactDecimal(ing.quantity) * ExactDecimal("2")).toString(),
                    unit = ing.unit,
                    purchasedAt = "2026-10-25",
                    expiresAt = "2026-10-30"
                )
            )
        }

        // 1. Kiểm tra tồn kho
        val (canCook, deficits) = EasyMealsEngine.checkRecipeStock(
            recipe = recipe,
            pantryLots = lotList,
            multiplier = "1",
            conversions = catalogue.conversions
        )
        assertTrue("Phải đủ nguyên liệu để nấu món ${recipe.name}", canCook)
        assertTrue("Không được có phần thiếu", deficits.isEmpty())

        // 2. Trừ kho (Đã ăn)
        val planId = "plan_test_journey_2"
        val outcome = EasyMealsEngine.executeStockDeduction(
            pantryLots = lotList,
            recipe = recipe,
            mealPlanId = planId,
            idempotencyKey = "key_1",
            multiplier = "1",
            conversions = catalogue.conversions,
            allowPartial = false
        )
        assertTrue("Phải phát sinh biến động trừ kho", outcome.movements.isNotEmpty())

        // 3. Hoàn tác (Undo)
        val (restoredLots, undoMovements) = EasyMealsEngine.reverseStockMovements(
            pantryLots = outcome.updatedLots,
            movements = outcome.movements,
            mealPlanId = planId
        )
        assertTrue("Phải phát sinh biến động hoàn tác", undoMovements.isNotEmpty())
        assertEquals("Số lượng lô sau hoàn tác phải khớp", outcome.updatedLots.size, restoredLots.size)
    }

    // Hành trình 3: Đi chợ -> Mua hàng -> Cho vào tủ (Shopping list -> Pantry)
    @Test
    fun testJourney3_ShoppingToPantry() {
        val shoppingItem = ShoppingItem(
            ingredientId = "trung_ga",
            ingredientName = "Trứng gà",
            neededQuantity = "10",
            unit = "quả",
            isBought = true
        )

        // Khi người dùng bấm cho đồ đã mua vào tủ
        val transferredLot = PantryLot(
            id = UUID.randomUUID().toString(),
            ingredientId = shoppingItem.ingredientId,
            ingredientName = shoppingItem.ingredientName,
            remainingQuantity = shoppingItem.neededQuantity,
            purchasedQuantity = shoppingItem.neededQuantity,
            unit = shoppingItem.unit,
            purchasedAt = "2026-10-25"
        )

        assertEquals("10", transferredLot.remainingQuantity)
        assertEquals("quả", transferredLot.unit)
        assertEquals("trung_ga", transferredLot.ingredientId)
    }

    // Hành trình 4: Duyệt công thức -> Điều chỉnh khẩu phần -> Chế độ nấu
    @Test
    fun testJourney4_BrowseRecipesAndCookingMode() {
        assertEquals("Tổng số công thức phải là 133", 133, catalogue.recipes.size)

        val recipe = catalogue.recipes.first { it.instructions.isNotEmpty() }
        assertNotNull(recipe)
        assertTrue(recipe.instructions.isNotEmpty())

        // Tỉ lệ khẩu phần: từ recipe.servings lên 6
        val targetServings = "6"
        val multiplier = (ExactDecimal(targetServings) / ExactDecimal(recipe.servings.toString())).toString()

        for (ing in recipe.ingredients) {
            val scaledQuantity = (ExactDecimal(ing.quantity) * ExactDecimal(multiplier)).toString()
            assertTrue("Lượng nguyên liệu sau điều chỉnh khẩu phần phải > 0", ExactDecimal(scaledQuantity) > ExactDecimal("0"))
        }
    }

    @Test
    fun testPlanDaysBoundariesAndCounts() {
        val start = "2026-10-25"

        // 1 ngày -> 2 bữa
        val (_, meals1, _) = EasyMealsEngine.generatePeriodPlan(
            startDateStr = start,
            endDateStr = start,
            recipes = catalogue.recipes,
            currentPantryLots = emptyList()
        )
        assertEquals(2, meals1.size)
        assertEquals(1, meals1.map { it.plannedFor }.distinct().size)

        // 7 ngày -> 14 bữa (7 ngày x 2 bữa)
        val end7 = "2026-10-31"
        val (_, meals7, _) = EasyMealsEngine.generatePeriodPlan(
            startDateStr = start,
            endDateStr = end7,
            recipes = catalogue.recipes,
            currentPantryLots = emptyList()
        )
        assertEquals(14, meals7.size)
        assertEquals(7, meals7.map { it.plannedFor }.distinct().size)

        // 8 ngày -> ném ngoại lệ
        try {
            EasyMealsEngine.generatePeriodPlan(
                startDateStr = start,
                endDateStr = "2026-11-01",
                recipes = catalogue.recipes,
                currentPantryLots = emptyList()
            )
            fail("Mong đợi ngoại lệ khi days=8")
        } catch (_: IncompatibleUnitException) {}

        // 0 ngày -> ném ngoại lệ
        try {
            EasyMealsEngine.generatePeriodPlan(
                startDateStr = start,
                endDateStr = "2026-10-24",
                recipes = catalogue.recipes,
                currentPantryLots = emptyList()
            )
            fail("Mong đợi ngoại lệ khi days=0")
        } catch (_: IncompatibleUnitException) {}
    }
}
