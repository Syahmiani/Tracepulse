package com.tracepulse

import android.hardware.biometrics.BiometricPrompt
import android.os.Handler
import android.os.Looper

class TracePulseUnlockAuthorizer(private val context: Context) {
    private val biometricPrompt = BiometricPrompt(
        context,
        object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                super.onAuthenticationSucceeded(result)
                println("Biometric authentication succeeded")
            }
        }
    )

    private val promptInfo = BiometricPrompt.PromptInfo.Builder()
        .setTitle("TracePulse Unlock")
        .setSubtitle("Authenticate to unlock")
        .setNegativeButtonText("Cancel")
        .build()

    fun authorizeUnlock() {
        Handler(Looper.getMainLooper()).post {
            biometricPrompt.authenticate(promptInfo)
        }
    }
}