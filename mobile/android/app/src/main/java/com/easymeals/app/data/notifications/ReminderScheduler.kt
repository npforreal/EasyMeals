package com.easymeals.app.data.notifications

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.content.getSystemService
import com.easymeals.app.domain.reminders.ReminderPlanner
import java.time.ZonedDateTime

/**
 * F2 - Vòng 13: lên lịch nhắc việc cục bộ bằng AlarmManager.
 *
 * Không dùng mạng, không dùng exact-alarm (không xin thêm quyền) — hệ thống có thể
 * gửi trễ vài phút so với 09:00. Mỗi lần báo xong, [ReminderReceiver] tự lên lịch
 * cho ngày kế tiếp; mở ứng dụng cũng lên lịch lại (xử lý trường hợp máy khởi động lại).
 */
object ReminderScheduler {

    const val CHANNEL_ID = "easymeals_reminders"
    const val NOTIFICATION_ID = 9001

    private const val REQUEST_CODE = 9001
    private const val PREFS_NAME = "easymeals_prefs"
    private const val PREF_ENABLED = "reminders_enabled"

    fun isEnabled(context: Context): Boolean =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getBoolean(PREF_ENABLED, false)

    fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService<NotificationManager>() ?: return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Nhắc việc EasyMeals",
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = "Nhắc hạn dùng thực phẩm và bữa ăn trong ngày. Hoàn toàn cục bộ trên máy."
            setShowBadge(true)
        }
        manager.createNotificationChannel(channel)
    }

    /** Lên lịch mốc 09:00 kế tiếp; an toàn khi gọi lặp (alarm cùng PendingIntent được thay thế). */
    fun scheduleNext(context: Context, now: ZonedDateTime = ZonedDateTime.now()) {
        val trigger = ReminderPlanner.nextTrigger(now)
        val alarmManager = context.getSystemService<AlarmManager>() ?: return
        alarmManager.setAndAllowWhileIdle(
            AlarmManager.RTC_WAKEUP,
            trigger.toInstant().toEpochMilli(),
            pendingIntent(context)
        )
    }

    fun cancel(context: Context) {
        val alarmManager = context.getSystemService<AlarmManager>() ?: return
        alarmManager.cancel(pendingIntent(context))
    }

    /** Bật -> lên lịch; tắt -> huỷ. Gọi khi mở app và khi người dùng đổi công tắc. */
    fun applySetting(context: Context) {
        if (isEnabled(context)) {
            ensureChannel(context)
            scheduleNext(context)
        } else {
            cancel(context)
        }
    }

    private fun pendingIntent(context: Context): PendingIntent {
        val intent = Intent(context, ReminderReceiver::class.java).apply {
            action = ReminderReceiver.ACTION_DAILY_REMINDER
        }
        return PendingIntent.getBroadcast(
            context,
            REQUEST_CODE,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }
}
