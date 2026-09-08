package com.example.iotvoice

import android.content.Context
import android.media.AudioManager
import io.livekit.android.LiveKit
import io.livekit.android.room.Room
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class VoiceAssistantController(
    private val context: Context,
    private val scope: CoroutineScope,
    private val apiBaseUrl: String,
    picovoiceAccessKey: String,
) {
    private var room: Room? = null
    private var sessionJob: Job? = null
    private val http = OkHttpClient()
    private val wakeWord = WakeWordManager(context, picovoiceAccessKey) { onWakeWord() }

    fun start() = wakeWord.start()

    fun stop() {
        sessionJob?.cancel()
        room?.disconnect()
        room = null
        wakeWord.stop()
    }

    private fun onWakeWord() {
        playChime()
        sessionJob = scope.launch(Dispatchers.Main) {
            try {
                val session = fetchSessionToken()
                val liveKit = LiveKit.create(context)
                room = liveKit.connect(session.wsUrl, session.token)
                room?.localParticipant?.setMicrophoneEnabled(true)
                delay(60_000)
                resetToSleeping()
            } catch (_: Exception) {
                resetToSleeping()
            }
        }
    }

    private fun resetToSleeping() {
        room?.localParticipant?.setMicrophoneEnabled(false)
        room?.disconnect()
        room = null
        sessionJob = null
        wakeWord.start()
    }

    private fun playChime() {
        val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audio.playSoundEffect(AudioManager.FX_KEYPRESS_STANDARD)
    }

    private data class Session(val token: String, val wsUrl: String)

    private fun fetchSessionToken(): Session {
        val body = "{\"user_id\":\"android-device\",\"room_name\":\"iot-control-room\"}"
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder().url("$apiBaseUrl/api/v1/session/token").post(body).build()
        http.newCall(request).execute().use { response ->
            check(response.isSuccessful) { "Token request failed: ${response.code}" }
            val json = JSONObject(response.body!!.string())
            return Session(json.getString("token"), json.getString("ws_url"))
        }
    }
}
