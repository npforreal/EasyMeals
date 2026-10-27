package com.easymeals.app.data.notifications

import android.Manifest
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.easymeals.app.MainActivity
import com.easymeals.app.R
import com.easymeals.app.data.db.AppRepository
import com.easymeals.app.domain.reminders.ReminderPlanner
import java.time.LocalDate

/**
 * F2: nhận alarm hằng ngày, dựng nội dung từ dữ liệu cục bộ rồi hiển thị thông báo.
 *
 * Receiver không được export (chỉ alarm nội bộ của ứng dụng kích hoạt) và không
 * ghi log nội dung tủ lạnh/thực đơn.
 */
class ReminderReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action != ACTION_DAILY_REMINDER) return
        if (!ReminderScheduler.isEnabled(context)) return

        // Android 13+: không có quyền thì bỏ qua, không thử hiển thị.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            ReminderScheduler.cancel(context)
            return
        }

        val appContext = context.applicationContext
        val repository = AppRepository(appContext)
        val digest = ReminderPlanner.buildDigest(
            pantryLots = repository.pantryLots.value,
            mealPlans = repository.mealPlans.value,
            date = LocalDate.now()
        )

        if (digest != null) {
            ReminderScheduler.ensureChannel(appContext)
            val openApp = PendingIntent.getActivity(
                appContext,
                0,
                Intent(appContext, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                },
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            val notification = NotificationCompat.Builder(appContext, ReminderScheduler.CHANNEL_ID)
                .setSmallIcon(R.mipmap.ic_launcher_foreground)
                .setContentTitle(digest.title)
                .setContentText(digest.body.lineSequence().firstOrNull() ?: "")
                .setStyle(NotificationCompat.BigTextStyle().bigText(digest.body))
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .setContentIntent(openApp)
                .build()
            NotificationManagerCompat.from(appContext)
                .notify(ReminderScheduler.NOTIFICATION_ID, notification)
        }

        // Lên lịch cho ngày kế tiếp (alarm một lần, không dựa vào repeating để đúng giờ địa phương).
        ReminderScheduler.scheduleNext(appContext)
    }

    companion object {
        const val ACTION_DAILY_REMINDER = "com.easymeals.app.action.DAILY_REMINDER"
    }
}
