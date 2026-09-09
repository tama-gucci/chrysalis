package com.chrysalis.mobile.chrysalis_mobile

import androidx.activity.result.ActivityResultLauncher
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.lifecycleScope
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : FlutterActivity() {
    private val channelName = "org.chrysalis.mobile/health_connect"
    private lateinit var healthConnectManager: HealthConnectManager
    private var pendingPermissionResult: MethodChannel.Result? = null

    private val requestPermissionLauncher: ActivityResultLauncher<Set<String>> =
        registerForActivityResult(PermissionController.createRequestPermissionResultContract()) { _ ->
            lifecycleScope.launch {
                val hasAll = withContext(Dispatchers.IO) {
                    healthConnectManager.hasPermissions()
                }
                pendingPermissionResult?.success(hasAll)
                pendingPermissionResult = null
            }
        }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        healthConnectManager = HealthConnectManager(applicationContext)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName).setMethodCallHandler { call, result ->
            when (call.method) {
                "isAvailable" -> {
                    result.success(healthConnectManager.isAvailable())
                }
                "hasPermissions" -> {
                    lifecycleScope.launch {
                        try {
                            val has = withContext(Dispatchers.IO) {
                                healthConnectManager.hasPermissions()
                            }
                            result.success(has)
                        } catch (e: Exception) {
                            result.error("PERMISSION_ERROR", e.message, null)
                        }
                    }
                }
                "requestPermissions" -> {
                    if (!healthConnectManager.isAvailable()) {
                        result.success(false)
                        return@setMethodCallHandler
                    }

                    lifecycleScope.launch {
                        try {
                            val alreadyGranted = withContext(Dispatchers.IO) {
                                healthConnectManager.hasPermissions()
                            }
                            if (alreadyGranted) {
                                result.success(true)
                            } else {
                                pendingPermissionResult = result
                                requestPermissionLauncher.launch(healthConnectManager.permissions)
                            }
                        } catch (e: Exception) {
                            result.error("PERMISSION_REQUEST_ERROR", e.message, null)
                        }
                    }
                }
                "getTelemetryForDate" -> {
                    val dateStr = call.argument<String>("date")
                    if (dateStr == null) {
                        result.error("INVALID_ARGUMENT", "date parameter is required", null)
                        return@setMethodCallHandler
                    }

                    lifecycleScope.launch {
                        try {
                            val telemetry = withContext(Dispatchers.IO) {
                                healthConnectManager.getTelemetryForDate(dateStr)
                            }
                            result.success(telemetry)
                        } catch (e: Exception) {
                            result.error("TELEMETRY_ERROR", e.message, null)
                        }
                    }
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
    }
}
