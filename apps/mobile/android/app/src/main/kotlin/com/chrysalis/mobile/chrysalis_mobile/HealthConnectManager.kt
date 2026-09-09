package com.chrysalis.mobile.chrysalis_mobile

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.HeartRateVariabilityRmssdRecord
import androidx.health.connect.client.records.RestingHeartRateRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * Native Android manager for Google Health Connect API (androidx.health.connect.client).
 *
 * Reads:
 * - SleepSessionRecord and fine-grained SleepSessionRecord.Stage intervals (deep, rem, light, awake)
 * - RestingHeartRateRecord (resting BPM)
 * - HeartRateVariabilityRmssdRecord (HRV RMSSD in milliseconds)
 */
class HealthConnectManager(private val context: Context) {

    private val client: HealthConnectClient? by lazy {
        if (isAvailable()) {
            HealthConnectClient.getOrCreate(context)
        } else {
            null
        }
    }

    val permissions = setOf(
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class),
        HealthPermission.getReadPermission(RestingHeartRateRecord::class),
        HealthPermission.getReadPermission(HeartRateVariabilityRmssdRecord::class)
    )

    fun isAvailable(): Boolean {
        return try {
            HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE
        } catch (e: Exception) {
            false
        }
    }

    suspend fun hasPermissions(): Boolean {
        val currentClient = client ?: return false
        val granted = currentClient.permissionController.getGrantedPermissions()
        return granted.containsAll(permissions)
    }

    suspend fun getTelemetryForDate(dateStr: String): Map<String, Any?> {
        val currentClient = client ?: return emptyMap()

        // Parse target date and establish a search window from previous evening (18:00) to current afternoon (14:00)
        val cleanDate = if (dateStr.length >= 10) dateStr.substring(0, 10) else dateStr
        val targetDate = try {
            LocalDate.parse(cleanDate)
        } catch (e: Exception) {
            LocalDate.now()
        }
        val zone = ZoneId.systemDefault()

        val windowStart = targetDate.minusDays(1).atTime(18, 0).atZone(zone).toInstant()
        val windowEnd = targetDate.atTime(14, 0).atZone(zone).toInstant()

        // 1. Read Sleep Sessions
        val sleepRequest = ReadRecordsRequest(
            recordType = SleepSessionRecord::class,
            timeRangeFilter = TimeRangeFilter.between(windowStart, windowEnd)
        )
        val sleepResponse = currentClient.readRecords(sleepRequest)
        val sleepSession = sleepResponse.records.maxByOrNull { it.endTime }

        var sleepMap: Map<String, Any?>? = null
        if (sleepSession != null) {
            var deepMinutes = 0
            var remMinutes = 0
            var lightMinutes = 0
            var awakeMinutes = 0
            val intervals = mutableListOf<Map<String, String>>()

            for (stage in sleepSession.stages) {
                val stageDuration = Duration.between(stage.startTime, stage.endTime).toMinutes().toInt()
                val stageTypeStr = when (stage.stage) {
                    SleepSessionRecord.STAGE_TYPE_DEEP -> {
                        deepMinutes += stageDuration
                        "deep"
                    }
                    SleepSessionRecord.STAGE_TYPE_REM -> {
                        remMinutes += stageDuration
                        "rem"
                    }
                    SleepSessionRecord.STAGE_TYPE_AWAKE,
                    SleepSessionRecord.STAGE_TYPE_OUT_OF_BED -> {
                        awakeMinutes += stageDuration
                        "awake"
                    }
                    SleepSessionRecord.STAGE_TYPE_LIGHT,
                    SleepSessionRecord.STAGE_TYPE_SLEEPING -> {
                        lightMinutes += stageDuration
                        "light"
                    }
                    else -> {
                        lightMinutes += stageDuration
                        "light"
                    }
                }

                intervals.add(
                    mapOf(
                        "stage" to stageTypeStr,
                        "startTime" to stage.startTime.toString(),
                        "endTime" to stage.endTime.toString()
                    )
                )
            }

            val totalDurationMinutes = Duration.between(sleepSession.startTime, sleepSession.endTime).toMinutes().toInt()
            if (deepMinutes == 0 && remMinutes == 0 && lightMinutes == 0) {
                // If stages are not reported by device, assign all non-awake time to light sleep
                lightMinutes = totalDurationMinutes - awakeMinutes
            }

            val sleepMinutes = deepMinutes + remMinutes + lightMinutes
            val efficiency = if (totalDurationMinutes > 0) {
                (sleepMinutes.toDouble() / totalDurationMinutes.toDouble()) * 100.0
            } else {
                100.0
            }

            sleepMap = mapOf(
                "startTime" to sleepSession.startTime.toString(),
                "endTime" to sleepSession.endTime.toString(),
                "deepSleepMinutes" to deepMinutes,
                "remSleepMinutes" to remMinutes,
                "lightSleepMinutes" to lightMinutes,
                "awakeMinutes" to awakeMinutes,
                "efficiencyPercent" to efficiency,
                "intervals" to intervals
            )
        }

        // 2. Read Resting Heart Rate
        val rhrRequest = ReadRecordsRequest(
            recordType = RestingHeartRateRecord::class,
            timeRangeFilter = TimeRangeFilter.between(windowStart, windowEnd)
        )
        val rhrResponse = currentClient.readRecords(rhrRequest)
        val latestRhr = rhrResponse.records.maxByOrNull { it.time }

        var rhrMap: Map<String, Any?>? = null
        if (latestRhr != null) {
            rhrMap = mapOf(
                "timestamp" to latestRhr.time.toString(),
                "bpm" to latestRhr.beatsPerMinute.toInt()
            )
        }

        // 3. Read Heart Rate Variability (RMSSD)
        val hrvRequest = ReadRecordsRequest(
            recordType = HeartRateVariabilityRmssdRecord::class,
            timeRangeFilter = TimeRangeFilter.between(windowStart, windowEnd)
        )
        val hrvResponse = currentClient.readRecords(hrvRequest)
        val latestHrv = hrvResponse.records.maxByOrNull { it.time }

        var hrvMap: Map<String, Any?>? = null
        if (latestHrv != null) {
            hrvMap = mapOf(
                "timestamp" to latestHrv.time.toString(),
                "rmssdMillis" to latestHrv.heartRateVariabilityMillis
            )
        }

        return mapOf(
            "sleep" to sleepMap,
            "restingHeartRate" to rhrMap,
            "hrv" to hrvMap
        )
    }
}
