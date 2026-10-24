package com.easymeals.app.domain.engine

import com.easymeals.app.domain.model.*
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

    fun getTotalIngredientStock(pantryLots: List<PantryLot>, ingredientId: String, targetUnit: String): ExactDecimal {
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
        return total
    }

    fun consumeAvailable(
        pantryLots: MutableList<PantryLot>,
        ingredientId: String,
        quantity: ExactDecimal,
        unit: String
    ): ExactDecimal {
        var needed = quantity
        var consumed = ExactDecimal.ZERO

        pantryLots.sortBy { lotSortKey(it) }

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

        return consumed
    }

    fun checkRecipeStock(
        recipe: Recipe,
        pantryLots: List<PantryLot>,
        multiplier: String = "1"
    ): Pair<Boolean, Map<String, DeficitItem>> {
        val deficits = mutableMapOf<String, DeficitItem>()
        val requirements = aggregateRequirements(recipe, multiplier)

        for (req in requirements) {
            val available = getTotalIngredientStock(pantryLots, req.ingredientId, req.unit)
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

    fun deductRecipeStockFifo(
        pantryLots: List<PantryLot>,
        recipe: Recipe,
        mealPlanId: String,
        idempotencyKey: String,
        multiplier: String = "1"
    ): Pair<List<PantryLot>, List<StockMovement>> {
        val (canCook, deficits) = checkRecipeStock(recipe, pantryLots, multiplier)
        if (!canCook) {
            throw InsufficientStockException("Không đủ nguyên liệu để nấu món '${recipe.name}'", deficits)
        }

        val requirements = aggregateRequirements(recipe, multiplier)
        val clonedLots = pantryLots.map { it.copy() }.toMutableList()
        val reqIds = requirements.map { it.ingredientId }.toSet()

        val candidateLots = clonedLots.filter { reqIds.contains(it.ingredientId) }.toMutableList()
        candidateLots.sortBy { lotSortKey(it) }

        val updatedLotsMap = linkedMapOf<String, PantryLot>()
        val movements = mutableListOf<StockMovement>()

        for (req in requirements) {
            var remainingNeeded = req.quantity

            for (lot in candidateLots) {
                if (remainingNeeded <= ExactDecimal.ZERO) break
                if (lot.ingredientId != req.ingredientId || !UnitDimensions.areCompatible(lot.unit, req.unit)) continue
                val lotRem = ExactDecimal(lot.remainingQuantity)
                if (lotRem <= ExactDecimal.ZERO) continue

                val availableInReq = try {
                    UnitDimensions.convert(lotRem, lot.unit, req.unit)
                } catch (_: Exception) {
                    continue
                }

                val deductedLotUnit: ExactDecimal
                if (availableInReq <= remainingNeeded) {
                    deductedLotUnit = lotRem
                    lot.remainingQuantity = "0"
                    remainingNeeded -= availableInReq
                } else {
                    val deductedReqUnit = remainingNeeded
                    deductedLotUnit = try {
                        UnitDimensions.convert(deductedReqUnit, req.unit, lot.unit)
                    } catch (_: Exception) {
                        lotRem
                    }
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
                        idempotencyKey = "${idempotencyKey}_${lot.id}"
                    )
                )
            }
        }

        return Pair(updatedLotsMap.values.toList(), movements)
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
        allowLeftovers: Boolean = true
    ): Triple<String, List<MealPlan>, List<ShoppingItem>> {
        val formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd")
        val start = LocalDate.parse(startDateStr, formatter)
        val end = LocalDate.parse(endDateStr, formatter)

        val diffDays = ChronoUnit.DAYS.between(start, end).toInt() + 1
        if (diffDays <= 0) {
            throw IncompatibleUnitException("Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu.")
        }

        val periodId = UUID.randomUUID().toString()
        val recipesByCat = mapOf(
            "man" to recipes.filter { it.category == "man" },
            "rau" to recipes.filter { it.category == "rau" },
            "canh" to recipes.filter { it.category == "canh" }
        )

        val simulatedLots = currentPantryLots.map { it.copy() }.toMutableList()
        val cookedRecipeIds = mutableSetOf<String>()
        val availableLeftovers = mutableListOf<PlannedDish>()
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

                    // 1. Dùng thức ăn thừa
                    if (allowLeftovers && availableLeftovers.isNotEmpty()) {
                        val leftIdx = availableLeftovers.indexOfFirst { it.category == cat }
                        if (leftIdx != -1) {
                            val left = availableLeftovers.removeAt(leftIdx)
                            dishChosen = PlannedDish(
                                id = UUID.randomUUID().toString(),
                                mealPlanId = planId,
                                recipeId = left.recipeId,
                                recipeName = "${left.recipeName} (Ăn lại)",
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
                            val (canCook, _) = checkRecipeStock(r, usableLots)
                            if (canCook) {
                                fullyStocked = r
                                break
                            }
                        }

                        var chosen: Recipe? = null
                        if (fullyStocked != null) {
                            chosen = fullyStocked
                            for (req in aggregateRequirements(fullyStocked)) {
                                consumeAvailable(usableLots, req.ingredientId, req.quantity, req.unit)
                            }
                        } else if (candidates.isNotEmpty()) {
                            chosen = candidates.first()
                            val (_, deficits) = checkRecipeStock(chosen, usableLots)
                            for (req in aggregateRequirements(chosen)) {
                                consumeAvailable(usableLots, req.ingredientId, req.quantity, req.unit)
                            }
                            for ((ingId, def) in deficits) {
                                val dimStr = UnitDimensions.dimension(def.unit)?.name ?: "UNKNOWN"
                                val key = "$ingId|$dimStr"
                                val item = shoppingItemsMap[key]
                                if (item != null) {
                                    val missingDecimal = ExactDecimal(def.missingQuantity)
                                    val converted = try {
                                        UnitDimensions.convert(missingDecimal, def.unit, item.unit)
                                    } catch (_: Exception) {
                                        missingDecimal
                                    }
                                    item.neededQuantity = (ExactDecimal(item.neededQuantity) + converted).toString()
                                    if (!item.dishNames.contains(chosen.name)) {
                                        item.dishNames.add(chosen.name)
                                    }
                                } else {
                                    shoppingItemsMap[key] = ShoppingItem(
                                        ingredientId = ingId,
                                        ingredientName = def.ingredientName,
                                        neededQuantity = def.missingQuantity,
                                        unit = def.unit,
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
                                availableLeftovers.add(dish)
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
}
