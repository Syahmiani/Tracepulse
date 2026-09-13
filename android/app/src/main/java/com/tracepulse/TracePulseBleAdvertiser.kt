package com.tracepulse

import android.bluetooth.le.AdvertiseSettings
import android.bluetooth.le.BluetoothLeAdvertiser
import android.content.Context
import android.os.Handler
import android.os.Looper

class TracePulseBleAdvertiser(private val context: Context) {
    private val advertiser: BluetoothLeAdvertiser?
    private val handler = Handler(Looper.getMainLooper())

    init {
        val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        advertiser = bluetoothManager.bluetoothAdapter.bluetoothLeAdvertiser
    }

    fun startAdvertising() {
        if (advertiser == null) return

        val settings = AdvertiseSettings.Builder()
            .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_BALANCED)
            .setConnectable(true)
            .setTimeout(0)
            .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
            .build()

        val advertiseCallback = object : BluetoothLeAdvertiser.AdvertiseCallback() {
            override fun onStartSuccess(settingsInEffect: AdvertiseSettings?) {
                println("BLE Advertising started successfully")
            }

            override fun onStartFailure(errorCode: Int) {
                println("BLE Advertising failed: $errorCode")
            }
        }

        advertiser.startAdvertising(settings, null, advertiseCallback)
    }
}