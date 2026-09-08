package com.example.iotvoice

import ai.picovoice.porcupine.Porcupine
import ai.picovoice.porcupine.PorcupineException
import ai.picovoice.porcupine.PorcupineManager
import android.content.Context

class WakeWordManager(
    private val context: Context,
    private val accessKey: String,
    private val onWakeWordDetected: () -> Unit,
) {
    private var manager: PorcupineManager? = null

    fun start() {
        if (manager != null) return
        try {
            manager = PorcupineManager.Builder()
                .setAccessKey(accessKey)
                .setKeyword(Porcupine.BuiltInKeyword.COMPUTER)
                .setSensitivity(0.7f)
                .build(context) { keywordIndex ->
                    if (keywordIndex >= 0) {
                        stop()
                        onWakeWordDetected()
                    }
                }
            manager?.start()
        } catch (error: PorcupineException) {
            stop()
            throw error
        }
    }

    fun stop() {
        manager?.stop()
        manager?.delete()
        manager = null
    }
}
