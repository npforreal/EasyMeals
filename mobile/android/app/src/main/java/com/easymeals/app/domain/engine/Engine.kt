package com.easymeals.app.domain.engine

import com.easymeals.app.domain.model.*
import com.easymeals.app.ui.theme.GeneratedTokens
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit
import java.util.UUID

class IncompatibleUnitException(message: String) : RuntimeException(message)

class InsufficientStockException(
    message: String,
    val deficits: Map<String, DeficitItem> = emptyMap()
) : RuntimeException(message)

object UnitDimensions {
    private val dimensions = mapOf(
        "g" to UnitDimension.MASS,
        "kg" to UnitDimension.MASS,
        "ml" to UnitDimension.VOLUME,
        "l" to UnitDimension.VOLUME,
        "piece" to UnitDimension.COUNT
    )

    private val multipliers = mapOf(
        "g" to ExactDecimal("1"),
        "kg" to ExactDecimal("1000"),
        "ml" to ExactDecimal("1"),
        "l" to ExactDecimal("1000"),
        "piece" to ExactDecimal("1")
    )

    fun dimension(unit: String): UnitDimension? = dimensions[unit]

    fun areCompatible(a: String, b: String): Boolean {
        val da = dimension(a) ?: return false
        val db = dimension(b) ?: return false
        return da == db
    }

    fun convert(quantity: ExactDecimal, fromUnit: String, toUnit: String): ExactDecimal {
        if (fromUnit == toUnit) return quantity
        val dimFrom = dimension(fromUnit)
        val dimTo = dimension(toUnit)
        if (dimFrom == null || dimTo == null || dimFrom != dimTo) {
            throw IncompatibleUnitException(
                "Không thể chuyển đổi đơn vị '$fromUnit' sang '$toUnit' vì khác thứ nguyên."
            )
        }
        val multFrom = multipliers[fromUnit] ?: throw IncompatibleUnitException("Thiếu hệ số cho $fromUnit")
        val multTo = multipliers[toUnit] ?: throw IncompatibleUnitException("Thiếu hệ số cho $toUnit")
        val base = quantity * multFrom
        return base / multTo
    }
}

data class AggregatedRequirement(
    val ingredientId: String,
    val name: String,
    var quantity: ExactDecimal,
    val unit: String
)

object EasyMealsEngine {

    /**
     * Sổ cái phần dư của một mẻ nấu: mỗi mẻ nấu (≥ 4 khẩu phần) dư đúng một phần
     * ăn, dùng lại một lần trong quá hạn (ngày nấu + leftoverDays).
     * Mô hình khớp AvailableLeftover trong app/domain/planner.py.
     */
    class AvailableLeftover(
        val dish: PlannedDish,
        var portionsRemaining: Int,
        val deadline: LocalDate
    )

    /** Đồ dư dùng lại tối đa 2 ngày (mặc định), cấu hình được trong 1-3 ngày. */
    fun validateLeftoverDays(leftoverDays: Int) {
        val min = GeneratedTokens.PlanLimits.LEFTOVER_MIN_DAYS
        val max = GeneratedTokens.PlanLimits.LEFTOVER_MAX_DAYS
        if (leftoverDays < min || leftoverDays > max) {
            throw IllegalArgumentException(
                "Số ngày dùng lại đồ dư phải từ $min đến $max ngày."
            )
        }
    }

    fun aggregateRequirements(recipe: Recipe, multiplier: String = "1"): List<AggregatedRequirement> {
        val mult = ExactDecimal(multiplier)
        val merged = linkedMapOf<String, AggregatedRequirement>()

        for (req in recipe.ingredients) {
            val qty = ExactDecimal(req.quantity) * mult
            val dimStr = UnitDimensions.dimension(req.unit)?.name ?: "UNKNOWN"
            val key = "${req.ingredientId}|$dimStr"

            val existing = merged[key]
            if (existing != null) {
                val converted = try {
                    UnitDimensions.convert(qty, req.unit, existing.unit)
                } catch (_: Exception) {
                    qty
                }
                existing.quantity = existing.quantity + converted
            } else {
                merged[key] = AggregatedRequirement(
                    ingredientId = req.ingredientId,
                    name = req.ingredientName,
                    quantity = qty,
                    unit = req.unit
                )
            }
        }
        return merged.values.toList()
    }

    fun lotSortKey(lot: PantryLot): String {
        val exp = lot.expiresAt ?: "9999-12-31"
        val pur = lot.purchasedAt ?: "1970-01-01"
        return "${exp}_$pur"
    }

    fun findConversionsForTarget(
        ingredientId: String,
        conversions: List<Conversion>?
    ): List<Conversion> {
        if (conversions == null) return emptyList()
        return conversions.filter {
            it.toIngredientId == ingredientId && ExactDecimal(it.ratio) > ExactDecimal.ZERO
        }
    }

    fun getTotalIngredientStock(
        pantryLots: List<PantryLot>,
        ingredientId: String,
        targetUnit: String,
        conversions: List<Conversion>? = null
    ): ExactDecimal {
        var total = ExactDecimal.ZERO
        for (lot in pantryLots) {
            if (lot.ingredientId != ingredientId || !UnitDimensions.areCompatible(lot.unit, targetUnit)) {
                continue
            }
            val rem = ExactDecimal(lot.remainingQuantity)
            if (rem > ExactDecimal.ZERO) {
                val converted = try {
                    UnitDimensions.convert(rem, lot.unit, targetUnit)
                } catch (_: Exception) {
                    null
                }
                if (converted != null) {
                    total += converted
                }
            }
        }

        val targetConvs = findConversionsForTarget(ingredientId, conversions)
        for (conv in targetConvs) {
            if (!UnitDimensions.areCompatible(conv.toUnit, targetUnit)) continue
            val ratio = ExactDecimal(conv.ratio)
            for (lot in pantryLots) {
                if (lot.ingredientId == conv.fromIngredientId && UnitDimensions.areCompatible(lot.unit, conv.fromUnit)) {
                    val rem = ExactDecimal(lot.remainingQuantity)
                    if (rem > ExactDecimal.ZERO) {
                        val rawInFromUnit = try {
                            UnitDimensions.convert(rem, lot.unit, conv.fromUnit)
                        } catch (_: Exception) { null } ?: continue
                        val prodInToUnit = rawInFromUnit * ratio
                        val converted = try {
                            UnitDimensions.convert(prodInToUnit, conv.toUnit, targetUnit)
                        } catch (_: Exception) { null } ?: continue
                        total += converted
                    }
                }
            }
        }
        return total
    }

    fun consumeAvailable(
        pantryLots: MutableList<PantryLot>,
        ingredientId: String,
        quantity: ExactDecimal,
        unit: String,
        conversions: List<Conversion>? = null
    ): ExactDecimal {
        var needed = quantity
        var consumed = ExactDecimal.ZERO

        pantryLots.sortBy { lotSortKey(it) }

        // 1. Trừ lô trực tiếp trước
        for (lot in pantryLots) {
            if (needed <= ExactDecimal.ZERO) break
            if (lot.ingredientId != ingredientId || !UnitDimensions.areCompatible(lot.unit, unit)) continue
            val rem = ExactDecimal(lot.remainingQuantity)
            if (rem <= ExactDecimal.ZERO) continue

            val available = try {
                UnitDimensions.convert(rem, lot.unit, unit)
            } catch (_: Exception) {
                continue
            }

            val take = if (available < needed) available else needed
            val takeInLotUnit = if (take == available) rem else try {
                UnitDimensions.convert(take, unit, lot.unit)
            } catch (_: Exception) {
                rem
            }

            lot.remainingQuantity = (rem - takeInLotUnit).toString()
            needed -= take
            consumed += take
        }

        // 2. Trừ lô gốc qua quy đổi (FIFO)
        if (needed > ExactDecimal.ZERO) {
            val targetConvs = findConversionsForTarget(ingredientId, conversions)
            for (conv in targetConvs) {
                if (needed <= ExactDecimal.ZERO) break
                if (!UnitDimensions.areCompatible(conv.toUnit, unit)) continue
                val ratio = ExactDecimal(conv.ratio)
                for (lot in pantryLots) {
                    if (needed <= ExactDecimal.ZERO) break
                    if (lot.ingredientId != conv.fromIngredientId || !UnitDimensions.areCompatible(lot.unit, conv.fromUnit)) continue
                    val rem = ExactDecimal(lot.remainingQuantity)
                    if (rem <= ExactDecimal.ZERO) continue

                    val neededInToUnit = try {
                        UnitDimensions.convert(needed, unit, conv.toUnit)
                    } catch (_: Exception) { null } ?: continue
                    val neededRawInFromUnit = neededInToUnit / ratio
                    val rawAvailable = try {
                        UnitDimensions.convert(rem, lot.unit, conv.fromUnit)
                    } catch (_: Exception) { null } ?: continue
                    val takeRaw = if (rawAvailable < neededRawInFromUnit) rawAvailable else neededRawInFromUnit
                    val takeInLotUnit = if (takeRaw == rawAvailable) rem else try {
                        UnitDimensions.convert(takeRaw, conv.fromUnit, lot.unit)
                    } catch (_: Exception) { rem }

                    lot.remainingQuantity = (rem - takeInLotUnit).toString()
                    val yieldedInToUnit = takeRaw * ratio
                    val yieldedUnit = try {
                        UnitDimensions.convert(yieldedInToUnit, conv.toUnit, unit)
                    } catch (_: Exception) { null } ?: continue
                    needed -= yieldedUnit
                    consumed += yieldedUnit
                }
            }
        }

        return consumed
    }

    fun checkRecipeStock(
        recipe: Recipe,
        pantryLots: List<PantryLot>,
        multiplier: String = "1",
        conversions: List<Conversion>? = null
    ): Pair<Boolean, Map<String, DeficitItem>> {
        val deficits = mutableMapOf<String, DeficitItem>()
        val requirements = aggregateRequirements(recipe, multiplier)

        for (req in requirements) {
            val available = getTotalIngredientStock(pantryLots, req.ingredientId, req.unit, conversions)
            if (available < req.quantity) {
                val missing = req.quantity - available
                deficits[req.ingredientId] = DeficitItem(
                    ingredientName = req.name,
                    missingQuantity = missing.toString(),
                    unit = req.unit
                )
            }
        }
        return Pair(deficits.isEmpty(), deficits)
    }

    data class StockDeductionOutcome(
        val updatedLots: List<PantryLot>,
        val movements: List<StockMovement>,
        val deficits: Map<String, DeficitItem>
    )

    fun executeStockDeduction(
        pantryLots: List<PantryLot>,
        recipe: Recipe,
        mealPlanId: String,
        idempotencyKey: String,
        multiplier: String = "1",
        conversions: List<Conversion>? = null,
        allowPartial: Boolean = false
    ): StockDeductionOutcome {
        if (!allowPartial) {
            val (canCook, deficits) = checkRecipeStock(recipe, pantryLots, multiplier, conversions)
            if (!canCook) {
                throw InsufficientStockException("Không đủ nguyên liệu để nấu món '${recipe.name}'", deficits)
            }
        }

        val requirements = aggregateRequirements(recipe, multiplier)
        val clonedLots = pantryLots.map { it.copy() }.toMutableList()
        val updatedLotsMap = linkedMapOf<String, PantryLot>()
        val movements = mutableListOf<StockMovement>()
        val deficits = mutableMapOf<String, DeficitItem>()

        for (req in requirements) {
            var remainingNeeded = req.quantity

            // 1. Trừ các lô trực tiếp
            val directLots = clonedLots.filter {
                it.ingredientId == req.ingredientId &&
                UnitDimensions.areCompatible(it.unit, req.unit) &&
                ExactDecimal(it.remainingQuantity) > ExactDecimal.ZERO
            }.sortedBy { lotSortKey(it) }

            for (lot in directLots) {
                if (remainingNeeded <= ExactDecimal.ZERO) break
                val lotRem = ExactDecimal(lot.remainingQuantity)
                val availableInReq = try {
                    UnitDimensions.convert(lotRem, lot.unit, req.unit)
                } catch (_: Exception) { continue }

                val deductedLotUnit: ExactDecimal
                if (availableInReq <= remainingNeeded) {
                    deductedLotUnit = lotRem
                    lot.remainingQuantity = "0"
                    remainingNeeded -= availableInReq
                } else {
                    val deductedReqUnit = remainingNeeded
                    deductedLotUnit = try {
                        UnitDimensions.convert(deductedReqUnit, req.unit, lot.unit)
                    } catch (_: Exception) { lotRem }
                    lot.remainingQuantity = (lotRem - deductedLotUnit).toString()
                    remainingNeeded = ExactDecimal.ZERO
                }

                updatedLotsMap[lot.id] = lot
                movements.add(
                    StockMovement(
                        id = UUID.randomUUID().toString(),
                        pantryLotId = lot.id,
                        quantityDelta = "-$deductedLotUnit",
                        reason = "meal_consumption",
                        mealPlanId = mealPlanId,
                        idempotencyKey = "${idempotencyKey}_${lot.id}_${movements.size}"
                    )
                )
            }

            // 2. Trừ qua quy đổi
            if (remainingNeeded > ExactDecimal.ZERO) {
                val targetConvs = findConversionsForTarget(req.ingredientId, conversions)
                for (conv in targetConvs) {
                    if (remainingNeeded <= ExactDecimal.ZERO) break
                    if (!UnitDimensions.areCompatible(conv.toUnit, req.unit)) continue
                    val ratio = ExactDecimal(conv.ratio)

                    val rawLots = clonedLots.filter {
                        it.ingredientId == conv.fromIngredientId &&
                        UnitDimensions.areCompatible(it.unit, conv.fromUnit) &&
                        ExactDecimal(it.remainingQuantity) > ExactDecimal.ZERO
                    }.sortedBy { lotSortKey(it) }

                    for (lot in rawLots) {
                        if (remainingNeeded <= ExactDecimal.ZERO) break
                        val lotRem = ExactDecimal(lot.remainingQuantity)
                        val neededInToUnit = try {
                            UnitDimensions.convert(remainingNeeded, req.unit, conv.toUnit)
                        } catch (_: Exception) { null } ?: continue
                        val neededRawInFromUnit = neededInToUnit / ratio
                        val lotRawInFromUnit = try {
                            UnitDimensions.convert(lotRem, lot.unit, conv.fromUnit)
                        } catch (_: Exception) { null } ?: continue
                        val takeRaw = if (lotRawInFromUnit < neededRawInFromUnit) lotRawInFromUnit else neededRawInFromUnit
                        val takeLotUnit = if (takeRaw == lotRawInFromUnit) lotRem else try {
                            UnitDimensions.convert(takeRaw, conv.fromUnit, lot.unit)
                        } catch (_: Exception) { lotRem }

                        lot.remainingQuantity = (lotRem - takeLotUnit).toString()
                        val yieldedInToUnit = takeRaw * ratio
                        val yieldedReqUnit = try {
                            UnitDimensions.convert(yieldedInToUnit, conv.toUnit, req.unit)
                        } catch (_: Exception) { null } ?: continue
                        remainingNeeded -= yieldedReqUnit

                        updatedLotsMap[lot.id] = lot
                        movements.add(
                            StockMovement(
                                id = UUID.randomUUID().toString(),
                                pantryLotId = lot.id,
                                quantityDelta = "-$takeLotUnit",
                                reason = "meal_consumption",
                                mealPlanId = mealPlanId,
                                idempotencyKey = "${idempotencyKey}_${lot.id}_${movements.size}"
                            )
                        )
                    }
                }
            }

            if (remainingNeeded > ExactDecimal.ZERO) {
                deficits[req.ingredientId] = DeficitItem(
                    ingredientName = req.name,
                    missingQuantity = remainingNeeded.toString(),
                    unit = req.unit
                )
            }
        }

        return StockDeductionOutcome(updatedLotsMap.values.toList(), movements, deficits)
    }

    fun deductRecipeStockFifo(
        pantryLots: List<PantryLot>,
        recipe: Recipe,
        mealPlanId: String,
        idempotencyKey: String,
        multiplier: String = "1",
        conversions: List<Conversion>? = null
    ): Pair<List<PantryLot>, List<StockMovement>> {
        val outcome = executeStockDeduction(pantryLots, recipe, mealPlanId, idempotencyKey, multiplier, conversions, false)
        return Pair(outcome.updatedLots, outcome.movements)
    }

    fun deductRecipeStockAvailable(
        pantryLots: List<PantryLot>,
        recipe: Recipe,
        mealPlanId: String,
        idempotencyKey: String,
        multiplier: String = "1",
        conversions: List<Conversion>? = null
    ): StockDeductionOutcome {
        return executeStockDeduction(pantryLots, recipe, mealPlanId, idempotencyKey, multiplier, conversions, true)
    }

    fun reverseStockMovements(
        pantryLots: List<PantryLot>,
        movements: List<StockMovement>,
        mealPlanId: String
    ): Pair<List<PantryLot>, List<StockMovement>> {
        val lotMap = pantryLots.associateBy { it.id }.mapValues { it.value.copy() }.toMutableMap()
        val restoredLotsMap = linkedMapOf<String, PantryLot>()
        val reversalMovements = mutableListOf<StockMovement>()

        val alreadyReversed = movements
            .filter { it.idempotencyKey?.startsWith("reversal_") == true }
            .mapNotNull { it.idempotencyKey?.removePrefix("reversal_") }
            .toSet()

        val targetMovements = movements.filter {
            it.mealPlanId == mealPlanId &&
            it.reason == "meal_consumption" &&
            ExactDecimal(it.quantityDelta) < ExactDecimal.ZERO &&
            !alreadyReversed.contains(it.id)
        }

        for (mov in targetMovements) {
            val lot = lotMap[mov.pantryLotId] ?: continue
            val deltaAbs = ExactDecimal(mov.quantityDelta).abs()
            val currentRem = ExactDecimal(lot.remainingQuantity)
            val cap = ExactDecimal(lot.purchasedQuantity)
            val restored = currentRem + deltaAbs
            lot.remainingQuantity = (if (restored > cap) cap else restored).toString()

            lotMap[lot.id] = lot
            restoredLotsMap[lot.id] = lot

            reversalMovements.add(
                StockMovement(
                    id = UUID.randomUUID().toString(),
                    pantryLotId = lot.id,
                    quantityDelta = deltaAbs.toString(),
                    reason = "correction",
                    mealPlanId = mealPlanId,
                    idempotencyKey = "reversal_${mov.id}"
                )
            )
        }

        return Pair(restoredLotsMap.values.toList(), reversalMovements)
    }

    fun generatePeriodPlan(
        startDateStr: String,
        endDateStr: String,
        recipes: List<Recipe>,
        currentPantryLots: List<PantryLot>,
        allowLeftovers: Boolean = true,
        conversions: List<Conversion>? = null,
        rawIngredientNames: Map<String, String>? = null,
        leftoverDays: Int = GeneratedTokens.PlanLimits.LEFTOVER_DEFAULT_DAYS
    ): Triple<String, List<MealPlan>, List<ShoppingItem>> {
        validateLeftoverDays(leftoverDays)
        val formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd")
        val start = LocalDate.parse(startDateStr, formatter)
        val end = LocalDate.parse(endDateStr, formatter)

        val diffDays = ChronoUnit.DAYS.between(start, end).toInt() + 1
        if (diffDays < GeneratedTokens.PlanLimits.MIN_DAYS || diffDays > GeneratedTokens.PlanLimits.MAX_DAYS) {
            throw IncompatibleUnitException("Số ngày lập thực đơn phải từ ${GeneratedTokens.PlanLimits.MIN_DAYS} đến ${GeneratedTokens.PlanLimits.MAX_DAYS} ngày.")
        }

        val periodId = UUID.randomUUID().toString()
        val recipesByCat = mapOf(
            "man" to recipes.filter { it.category == "man" },
            "rau" to recipes.filter { it.category == "rau" },
            "canh" to recipes.filter { it.category == "canh" }
        )

        val simulatedLots = currentPantryLots.map { it.copy() }.toMutableList()
        val cookedRecipeIds = mutableSetOf<String>()
        // Sổ cái phần dư: mỗi mẻ nấu (≥ 4 khẩu phần) dư đúng một phần ăn, dùng lại
        // một lần trong quá hạn (ngày nấu + leftoverDays). Khớp planner.py / engine.js.
        val availableLeftovers = mutableListOf<AvailableLeftover>()
        val mealPlans = mutableListOf<MealPlan>()
        val shoppingItemsMap = linkedMapOf<String, ShoppingItem>()

        val periods = listOf("lunch", "dinner")
        var curr = start

        for (d in 0 until diffDays) {
            val dateStr = curr.format(formatter)
            val usableLots = simulatedLots.filter { lot ->
                val exp = lot.expiresAt ?: return@filter true
                exp >= dateStr
            }.toMutableList()

            for (p in periods) {
                val planId = UUID.randomUUID().toString()
                val plannedDishes = mutableListOf<PlannedDish>()

                for (cat in listOf("man", "rau", "canh")) {
                    var dishChosen: PlannedDish? = null

                    // 1. Dùng thức ăn thừa (chỉ phần còn hạn và chưa dùng)
                    if (allowLeftovers && availableLeftovers.isNotEmpty()) {
                        val leftIdx = availableLeftovers.indexOfFirst {
                            it.portionsRemaining > 0 && !curr.isAfter(it.deadline) && it.dish.category == cat
                        }
                        if (leftIdx != -1) {
                            val entry = availableLeftovers.removeAt(leftIdx)
                            entry.portionsRemaining -= 1
                            val left = entry.dish
                            dishChosen = PlannedDish(
                                id = UUID.randomUUID().toString(),
                                mealPlanId = planId,
                                recipeId = left.recipeId,
                                recipeName = left.recipeName,
                                category = cat,
                                isLeftover = true,
                                originalDishId = left.id,
                                servings = left.servings
                            )
                        }
                    }

                    // 2. Chọn món mới
                    if (dishChosen == null) {
                        val candidates = (recipesByCat[cat] ?: emptyList()).filter { !cookedRecipeIds.contains(it.id) }
                        var fullyStocked: Recipe? = null
                        for (r in candidates) {
                            val (canCook, _) = checkRecipeStock(r, usableLots, "1", conversions)
                            if (canCook) {
                                fullyStocked = r
                                break
                            }
                        }

                        var chosen: Recipe? = null
                        if (fullyStocked != null) {
                            chosen = fullyStocked
                            for (req in aggregateRequirements(fullyStocked)) {
                                consumeAvailable(usableLots, req.ingredientId, req.quantity, req.unit, conversions)
                            }
                        } else if (candidates.isNotEmpty()) {
                            chosen = candidates.first()
                            val (_, deficits) = checkRecipeStock(chosen, usableLots, "1", conversions)
                            for (req in aggregateRequirements(chosen)) {
                                consumeAvailable(usableLots, req.ingredientId, req.quantity, req.unit, conversions)
                            }
                            for ((ingId, def) in deficits) {
                                var actualIngId = ingId
                                var actualUnit = def.unit
                                var actualQty = def.missingQuantity
                                var actualName = def.ingredientName

                                val targetConvs = findConversionsForTarget(ingId, conversions)
                                if (targetConvs.isNotEmpty()) {
                                    val conv = targetConvs.first()
                                    val missingInTo = try {
                                        UnitDimensions.convert(ExactDecimal(def.missingQuantity), def.unit, conv.toUnit)
                                    } catch (_: Exception) { ExactDecimal(def.missingQuantity) }
                                    val rawNeeded = missingInTo / ExactDecimal(conv.ratio)
                                    actualIngId = conv.fromIngredientId
                                    actualUnit = conv.fromUnit
                                    actualQty = rawNeeded.toString()
                                    actualName = rawIngredientNames?.get(actualIngId) ?: "Nguyên liệu gốc cho ${def.ingredientName}"
                                }

                                val dimStr = UnitDimensions.dimension(actualUnit)?.name ?: "UNKNOWN"
                                val key = "$actualIngId|$dimStr"
                                val item = shoppingItemsMap[key]
                                if (item != null) {
                                    val missingDecimal = ExactDecimal(actualQty)
                                    val converted = try {
                                        UnitDimensions.convert(missingDecimal, actualUnit, item.unit)
                                    } catch (_: Exception) {
                                        missingDecimal
                                    }
                                    item.neededQuantity = (ExactDecimal(item.neededQuantity) + converted).toString()
                                    if (!item.dishNames.contains(chosen.name)) {
                                        item.dishNames.add(chosen.name)
                                    }
                                } else {
                                    shoppingItemsMap[key] = ShoppingItem(
                                        ingredientId = actualIngId,
                                        ingredientName = actualName,
                                        neededQuantity = actualQty,
                                        unit = actualUnit,
                                        dishNames = mutableListOf(chosen.name)
                                    )
                                }
                            }
                        }

                        if (chosen != null) {
                            val dish = PlannedDish(
                                id = UUID.randomUUID().toString(),
                                mealPlanId = planId,
                                recipeId = chosen.id,
                                recipeName = chosen.name,
                                category = cat,
                                isLeftover = false,
                                servings = chosen.servings
                            )
                            dishChosen = dish
                            cookedRecipeIds.add(chosen.id)

                            if (allowLeftovers && chosen.servings >= 4) {
                                availableLeftovers.add(AvailableLeftover(dish, 1, curr.plusDays(leftoverDays.toLong())))
                            }
                        }
                    }

                    if (dishChosen != null) {
                        plannedDishes.add(dishChosen)
                    }
                }

                val plan = MealPlan(
                    id = planId,
                    plannedFor = dateStr,
                    mealPeriod = p,
                    periodId = periodId,
                    dishes = plannedDishes
                )
                mealPlans.add(plan)
            }
            curr = curr.plusDays(1)
        }

        return Triple(periodId, mealPlans, shoppingItemsMap.values.toList())
    }

    /**
     * Gộp đợt thực đơn mới vào thực đơn cũ an toàn (A2 - Vòng 13).
     * Quy tắc khớp merge_new_plans_into_existing (planner.py) và mergeNewPlansIntoExisting (engine.js):
     *   - Bữa đã ăn luôn được giữ; bữa chưa ăn trong khoảng ngày mới bị thay;
     *   - bữa chưa ăn ngoài khoảng ngày giữ nguyên; mọi bữa của đợt mới đều giữ.
     * Bản ghi trùng id được khử (idempotency theo mã định danh bữa).
     */
    fun mergeNewPlansIntoExisting(
        existing: List<MealPlan>,
        newPlans: List<MealPlan>,
        mode: String = "replace"
    ): List<MealPlan> {
        require(mode == "replace" || mode == "keep") { "Chế độ gộp thực đơn không hợp lệ: $mode" }
        if (newPlans.isEmpty()) return existing
        val rangeStart = newPlans.minOf { it.plannedFor }
        val rangeEnd = newPlans.maxOf { it.plannedFor }

        val kept = mutableListOf<MealPlan>()
        val seenIds = mutableSetOf<String>()
        for (plan in existing) {
            if (!seenIds.add(plan.id)) continue
            if (mode == "replace" && plan.eatenAt == null &&
                plan.plannedFor >= rangeStart && plan.plannedFor <= rangeEnd
            ) {
                continue
            }
            kept.add(plan)
        }
        if (mode == "keep") {
            val coveredDates = existing.map { it.plannedFor }.toSet()
            for (plan in newPlans) {
                if (!seenIds.add(plan.id)) continue
                if (plan.plannedFor in coveredDates) continue
                kept.add(plan)
            }
        } else {
            for (plan in newPlans) {
                if (!seenIds.add(plan.id)) continue
                kept.add(plan)
            }
        }
        return kept
    }

    data class ShoppingBudgetResult(
        val totalEstimatedBudget: String,
        val totalSpent: String,
        val itemsWithPriceCount: Int,
        val totalItemsCount: Int
    )

    fun calculateShoppingBudget(items: List<ShoppingItem>): ShoppingBudgetResult {
        var totalEstimated = ExactDecimal.ZERO
        var totalSpent = ExactDecimal.ZERO
        var itemsWithPrice = 0

        for (it in items) {
            val pStr = it.price
            if (!pStr.isNullOrBlank()) {
                val p = ExactDecimal(pStr)
                if (p > ExactDecimal.ZERO) {
                    totalEstimated = totalEstimated + p
                    itemsWithPrice++
                    if (it.isBought) {
                        totalSpent = totalSpent + p
                    }
                }
            }
        }

        return ShoppingBudgetResult(
            totalEstimatedBudget = totalEstimated.toString(),
            totalSpent = totalSpent.toString(),
            itemsWithPriceCount = itemsWithPrice,
            totalItemsCount = items.size
        )
    }

    fun groupShoppingItemsByCategory(
        items: List<ShoppingItem>,
        categoriesOrder: List<String> = listOf(
            "thit", "gia_cam", "hai_san", "trung_sua", "rau_cu",
            "cu_qua", "gao_bot_mi", "gia_vi", "nuoc_cham_dau", "khac"
        )
    ): Map<String, List<ShoppingItem>> {
        val grouped = categoriesOrder.associateWith { mutableListOf<ShoppingItem>() }.toMutableMap()
        for (it in items) {
            val cat = it.category ?: "khac"
            val targetList = grouped.getOrPut(cat) { mutableListOf() }
            targetList.add(it)
        }
        return grouped.filterValues { it.isNotEmpty() }
    }

    fun regenerateSingleMeal(
        targetMealPlanId: String,
        allMealPlans: List<MealPlan>,
        recipes: List<Recipe>,
        currentPantryLots: List<PantryLot> = emptyList(),
        conversions: List<Conversion>? = null
    ): MealPlan {
        val targetPlan = allMealPlans.find { it.id == targetMealPlanId }
            ?: throw IllegalArgumentException("Không tìm thấy bữa ăn có ID $targetMealPlanId")

        if (targetPlan.eatenAt != null) {
            throw IllegalStateException("Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. Hãy hoàn tác bữa ăn trước nếu bạn muốn đổi món.")
        }

        val otherCookedRecipeIds = mutableSetOf<String>()
        for (p in allMealPlans) {
            if (p.id == targetMealPlanId) continue
            for (d in p.dishes) {
                if (!d.isLeftover) {
                    otherCookedRecipeIds.add(d.recipeId)
                }
            }
        }

        val recipesByCat = mapOf(
            "man" to recipes.filter { it.category == "man" },
            "rau" to recipes.filter { it.category == "rau" },
            "canh" to recipes.filter { it.category == "canh" }
        )

        val planDate = LocalDate.parse(targetPlan.plannedFor.substring(0, 10))
        val usableLots = currentPantryLots.filter { lot ->
            lot.expiresAt == null || !LocalDate.parse(lot.expiresAt).isBefore(planDate)
        }.map { it.copy() }.toMutableList()

        val newDishes = mutableListOf<PlannedDish>()
        for (cat in listOf("man", "rau", "canh")) {
            val candidates = (recipesByCat[cat] ?: emptyList()).filter { !otherCookedRecipeIds.contains(it.id) }
                .ifEmpty { (recipesByCat[cat] ?: emptyList()).filter { r -> !newDishes.any { it.recipeId == r.id } } }

            var chosen: Recipe? = null
            for (r in candidates) {
                val (canCook, _) = checkRecipeStock(r, usableLots, "1", conversions)
                if (canCook) {
                    chosen = r
                    break
                }
            }
            if (chosen == null && candidates.isNotEmpty()) {
                chosen = candidates.first()
            }

            if (chosen != null) {
                for (req in aggregateRequirements(chosen)) {
                    consumeAvailable(usableLots, req.ingredientId, req.quantity, req.unit, conversions)
                }
                newDishes.add(
                    PlannedDish(
                        id = UUID.randomUUID().toString(),
                        mealPlanId = targetPlan.id,
                        recipeId = chosen.id,
                        recipeName = chosen.name,
                        category = cat,
                        isLeftover = false,
                        servings = chosen.servings
                    )
                )
            }
        }

        return targetPlan.copy(eatenAt = null, dishes = newDishes)
    }

    fun recomputeShoppingList(
        mealPlans: List<MealPlan>,
        currentPantryLots: List<PantryLot> = emptyList(),
        recipes: List<Recipe> = emptyList(),
        conversions: List<Conversion>? = null,
        rawIngredientNames: Map<String, String> = emptyMap(),
        ingredientCategories: Map<String, String> = emptyMap()
    ): List<ShoppingItem> {
        val recipesMap = recipes.associateBy { it.id }
        val simulatedLots = currentPantryLots.map { it.copy() }.toMutableList()
        val shoppingItemsMap = mutableMapOf<String, ShoppingItem>()

        val uneatenPlans = mealPlans.filter { it.eatenAt == null }
            .sortedBy { it.plannedFor }

        for (meal in uneatenPlans) {
            val mealDate = LocalDate.parse(meal.plannedFor.substring(0, 10))
            val usableLots = simulatedLots.filter { lot ->
                lot.expiresAt == null || !LocalDate.parse(lot.expiresAt).isBefore(mealDate)
            }.toMutableList()

            for (dish in meal.dishes) {
                if (dish.isLeftover) continue
                val recipe = recipesMap[dish.recipeId] ?: continue

                val (_, deficits) = checkRecipeStock(recipe, usableLots, "1", conversions)
                for (req in aggregateRequirements(recipe)) {
                    consumeAvailable(usableLots, req.ingredientId, req.quantity, req.unit, conversions)
                }

                for ((ingId, def) in deficits) {
                    val actualIngId: String
                    val actualUnit: String
                    val actualQty: String
                    val actualName: String

                    val targetConvs = findConversionsForTarget(ingId, conversions)
                    if (targetConvs.isNotEmpty()) {
                        val conv = targetConvs.first()
                        val missingInTo = UnitDimensions.convert(ExactDecimal(def.missingQuantity), def.unit, conv.toUnit)
                        val rawNeeded = missingInTo / ExactDecimal(conv.ratio)
                        actualIngId = conv.fromIngredientId
                        actualUnit = conv.fromUnit
                        actualQty = rawNeeded.toString()
                        actualName = rawIngredientNames[actualIngId] ?: "Nguyên liệu gốc cho ${def.ingredientName}"
                    } else {
                        actualIngId = ingId
                        actualUnit = def.unit
                        actualQty = def.missingQuantity
                        actualName = def.ingredientName
                    }

                    val dim = UnitDimensions.dimension(actualUnit)?.name ?: actualUnit
                    val key = "${actualIngId}_$dim"
                    val cat = ingredientCategories[actualIngId] ?: "khac"
                    val existing = shoppingItemsMap[key]

                    if (existing == null) {
                        shoppingItemsMap[key] = ShoppingItem(
                            ingredientId = actualIngId,
                            ingredientName = actualName,
                            neededQuantity = actualQty,
                            unit = actualUnit,
                            isBought = false,
                            isManuallyAdded = false,
                            dishNames = mutableListOf(recipe.name),
                            category = cat
                        )
                    } else {
                        val added = UnitDimensions.convert(ExactDecimal(actualQty), actualUnit, existing.unit)
                        existing.neededQuantity = (ExactDecimal(existing.neededQuantity) + added).toString()
                        if (!existing.dishNames.contains(recipe.name)) {
                            existing.dishNames.add(recipe.name)
                        }
                    }
                }
            }
        }

        return shoppingItemsMap.values.toList()
    }

    fun swapDishInMeal(
        mealPlan: MealPlan,
        oldDishId: String,
        newRecipe: Recipe,
        allPlansInPeriod: List<MealPlan> = emptyList()
    ): MealPlan {
        if (mealPlan.eatenAt != null) {
            throw IllegalStateException("Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. Hãy hoàn tác bữa ăn trước nếu bạn muốn đổi món.")
        }
        val dishes = mealPlan.dishes.toMutableList()
        val dishIdx = dishes.indexOfFirst { it.id == oldDishId }
        if (dishIdx == -1) {
            throw IllegalArgumentException("Không tìm thấy món có ID $oldDishId trong bữa ăn.")
        }

        if (allPlansInPeriod.isNotEmpty()) {
            val otherRecipeIds = allPlansInPeriod
                .flatMap { it.dishes }
                .filter { !it.isLeftover && (it.mealPlanId != mealPlan.id || it.id != oldDishId) }
                .map { it.recipeId }
                .toSet()
            if (otherRecipeIds.contains(newRecipe.id)) {
                throw IllegalArgumentException("Món '${newRecipe.name}' đã được lên lịch trong chu kỳ thực đơn này.")
            }
        }

        dishes[dishIdx] = PlannedDish(
            id = UUID.randomUUID().toString(),
            mealPlanId = mealPlan.id,
            recipeId = newRecipe.id,
            recipeName = newRecipe.name,
            category = newRecipe.category,
            servings = newRecipe.servings,
            isLeftover = false
        )
        return mealPlan.copy(dishes = dishes)
    }

    fun addDishToMeal(
        mealPlan: MealPlan,
        recipe: Recipe,
        servings: Int? = null
    ): MealPlan {
        if (mealPlan.eatenAt != null) {
            throw IllegalStateException("Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. Hãy hoàn tác bữa ăn trước nếu bạn muốn thêm món.")
        }
        if (mealPlan.dishes.any { it.recipeId == recipe.id }) {
            throw IllegalArgumentException("Món '${recipe.name}' đã có trong bữa ăn này.")
        }
        val catCount = mealPlan.dishes.count { it.category == recipe.category }
        if (catCount >= 2) {
            throw IllegalArgumentException("Bữa ăn đã đạt giới hạn tối đa 2 món cho nhóm ${recipe.category}.")
        }

        val dishes = mealPlan.dishes.toMutableList()
        dishes.add(
            PlannedDish(
                id = UUID.randomUUID().toString(),
                mealPlanId = mealPlan.id,
                recipeId = recipe.id,
                recipeName = recipe.name,
                category = recipe.category,
                servings = servings ?: recipe.servings,
                isLeftover = false
            )
        )
        return mealPlan.copy(dishes = dishes)
    }

    fun removeDishFromMeal(
        mealPlan: MealPlan,
        dishId: String
    ): MealPlan {
        if (mealPlan.eatenAt != null) {
            throw IllegalStateException("Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. Hãy hoàn tác bữa ăn trước nếu bạn muốn bỏ món.")
        }
        val dishes = mealPlan.dishes.toMutableList()
        val dishIdx = dishes.indexOfFirst { it.id == dishId }
        if (dishIdx == -1) {
            throw IllegalArgumentException("Không tìm thấy món có ID $dishId trong bữa ăn.")
        }
        if (dishes.size <= 1) {
            throw IllegalArgumentException("Không thể bỏ món duy nhất còn lại trong bữa ăn.")
        }
        dishes.removeAt(dishIdx)
        return mealPlan.copy(dishes = dishes)
    }

    fun rescheduleMeal(
        mealPlan: MealPlan,
        newDateStr: String,
        newPeriod: String,
        allMealPlans: List<MealPlan>
    ): MealPlan {
        if (mealPlan.eatenAt != null) {
            throw IllegalStateException("Bữa ăn này đã được đánh dấu ăn và ghi nhận vào kho. Hãy hoàn tác bữa ăn trước nếu bạn muốn chuyển ngày/bữa.")
        }
        val targetDate = newDateStr.substring(0, 10)
        val conflict = allMealPlans.any {
            it.id != mealPlan.id &&
            it.plannedFor.substring(0, 10) == targetDate &&
            it.mealPeriod == newPeriod
        }
        if (conflict) {
            val periodVn = if (newPeriod == "lunch") "trưa" else "tối"
            throw IllegalArgumentException("Đã có bữa ăn khác được lên lịch vào bữa $periodVn ngày $newDateStr.")
        }
        return mealPlan.copy(
            plannedFor = targetDate,
            mealPeriod = newPeriod
        )
    }

    fun mergeCompatibleShoppingItems(items: List<ShoppingItem>): List<ShoppingItem> {
        val mergedMap = mutableMapOf<String, ShoppingItem>()

        for (it in items) {
            val dim = UnitDimensions.dimension(it.unit)?.name ?: it.unit
            val key = "${it.ingredientId}_$dim"

            val existing = mergedMap[key]
            if (existing == null) {
                mergedMap[key] = it.copy(dishNames = it.dishNames.toMutableList())
            } else {
                val converted = UnitDimensions.convert(ExactDecimal(it.neededQuantity), it.unit, existing.unit)
                existing.neededQuantity = (ExactDecimal(existing.neededQuantity) + converted).toString()

                for (dn in it.dishNames) {
                    if (!existing.dishNames.contains(dn)) {
                        existing.dishNames.add(dn)
                    }
                }

                if (it.price != null && existing.price == null) {
                    existing.price = it.price
                } else if (it.price != null && existing.price != null) {
                    existing.price = (ExactDecimal(existing.price!!) + ExactDecimal(it.price!!)).toString()
                }

                existing.isBought = existing.isBought && it.isBought
            }
        }

        return mergedMap.values.toList()
    }
}
