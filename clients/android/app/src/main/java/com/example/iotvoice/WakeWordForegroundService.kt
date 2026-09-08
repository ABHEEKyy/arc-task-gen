package com.example.iotvoice

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.IBinder
import kotlinx.coroutines.*

class WakeWordForegroundService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private lateinit var controller: VoiceAssistantController

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(42, notification())
        controller = VoiceAssistantController(
            context = this,
            scope = scope,
            apiBaseUrl = BuildConfig.VOICE_API_URL,
            picovoiceAccessKey = BuildConfig.PICOVOICE_ACCESS_KEY,
        )
        controller.start()
    }

    override fun onDestroy() {
        controller.stop()
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        val channel = NotificationChannel("wake-word", "Voice assistant", NotificationManager.IMPORTANCE_LOW)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun notification(): Notification = Notification.Builder(this, "wake-word")
        .setContentTitle("Voice assistant active")
        .setContentText("Listening locally for the wake word")
        .setSmallIcon(android.R.drawable.ic_btn_speak_now)
        .build()
}
