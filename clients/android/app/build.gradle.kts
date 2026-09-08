plugins {
    id("com.android.application")
    kotlin("android")
}

android {
    namespace = "com.example.iotvoice"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.iotvoice"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        buildConfigField("String", "VOICE_API_URL", "\"http://10.0.2.2:8000\"")
        buildConfigField("String", "PICOVOICE_ACCESS_KEY", "\"REPLACE_WITH_PICOVOICE_KEY\"")
    }

    buildFeatures { buildConfig = true }
}

dependencies {
    implementation("androidx.activity:activity-ktx:1.10.0")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("ai.picovoice:porcupine-android:3.0.2")
    implementation("io.livekit:livekit-android:2.6.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
