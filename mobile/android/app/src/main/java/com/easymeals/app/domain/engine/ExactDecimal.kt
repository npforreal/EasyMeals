package com.easymeals.app.domain.engine

import java.math.BigDecimal
import java.math.RoundingMode

/**
 * Số học Decimal chính xác cho Android dựa trên java.math.BigDecimal.
 * Đồng nhất 100% với Python `Decimal` và JavaScript `Decimal` trong EasyMeals Engine.
 */
class ExactDecimal(val value: BigDecimal) : Comparable<ExactDecimal> {

    constructor(stringVal: String) : this(
        BigDecimal(stringVal.trim())
    )

    constructor(intVal: Int) : this(BigDecimal(intVal))
    constructor(longVal: Long) : this(BigDecimal(longVal))

    operator fun plus(other: ExactDecimal): ExactDecimal =
        ExactDecimal(this.value.add(other.value))

    operator fun minus(other: ExactDecimal): ExactDecimal =
        ExactDecimal(this.value.subtract(other.value))

    operator fun times(other: ExactDecimal): ExactDecimal =
        ExactDecimal(this.value.multiply(other.value))

    operator fun div(other: ExactDecimal): ExactDecimal {
        if (other.value.compareTo(BigDecimal.ZERO) == 0) {
            throw ArithmeticException("Phép chia cho 0 trong ExactDecimal")
        }
        // Giữ tối đa 6 chữ số thập phân tương đương fixed-point engine
        return try {
            ExactDecimal(this.value.divide(other.value))
        } catch (_: ArithmeticException) {
            ExactDecimal(this.value.divide(other.value, 6, RoundingMode.HALF_UP))
        }
    }

    override fun compareTo(other: ExactDecimal): Int =
        this.value.compareTo(other.value)

    fun abs(): ExactDecimal = ExactDecimal(this.value.abs())

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is ExactDecimal) return false
        return this.value.compareTo(other.value) == 0
    }

    override fun hashCode(): Int = this.value.stripTrailingZeros().hashCode()

    override fun toString(): String {
        if (value.compareTo(BigDecimal.ZERO) == 0) return "0"
        return value.stripTrailingZeros().toPlainString()
    }

    companion object {
        val ZERO = ExactDecimal(BigDecimal.ZERO)
        val ONE = ExactDecimal(BigDecimal.ONE)
    }
}
