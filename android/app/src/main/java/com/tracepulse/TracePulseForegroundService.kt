package com.tracepulse

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder

class TracePulseForegroundService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, createNotification())
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "TracePulse Service",
                NotificationManager.IMPORTANCE_LOW
            )
            val service = getSystemService(NotificationManager::class.java)
            service.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        return Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("TracePulse Running")
            .setContentText("Security service active")
            .setSmallIcon(android.R.drawable.ic_lock_idle_type)
            .build()
    }

    companion object {
        private const val CHANNEL_ID = "tracepulse_channel"
        private const val NOTIFICATION_ID = 1
    }
}