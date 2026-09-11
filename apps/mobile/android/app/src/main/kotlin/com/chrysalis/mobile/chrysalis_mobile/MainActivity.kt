package com.chrysalis.mobile.chrysalis_mobile

import android.content.ClipData
import android.content.ContentResolver
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.OpenableColumns
import android.util.Log
import android.webkit.MimeTypeMap
import android.widget.Toast
import androidx.activity.result.ActivityResultLauncher
import androidx.core.content.FileProvider
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.lifecycleScope
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream

class MainActivity : FlutterFragmentActivity() {
    private val healthChannelName = "org.chrysalis.mobile/health_connect"
    private val shareChannelName = "org.chrysalis.mobile/share_receiver"
    private lateinit var healthConnectManager: HealthConnectManager
    private var pendingPermissionResult: MethodChannel.Result? = null

    private var shareChannel: MethodChannel? = null
    private var pendingSharedPayload: Map<String, Any?>? = null
    private var activeProcessingCount = 0
    private var isLaunchedAsShareTarget = false

    private data class PendingPayloadRequest(
        val result: MethodChannel.Result,
        val shouldClear: Boolean
    )
    private val pendingPayloadRequests = mutableListOf<PendingPayloadRequest>()

    private val requestPermissionLauncher: ActivityResultLauncher<Set<String>> =
        registerForActivityResult(PermissionController.createRequestPermissionResultContract()) { _: Set<String> ->
            lifecycleScope.launch {
                val hasAll = withContext(Dispatchers.IO) {
                    healthConnectManager.hasPermissions()
                }
                pendingPermissionResult?.success(hasAll)
                pendingPermissionResult = null
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        isLaunchedAsShareTarget = isShareIntent(intent)
        handleShareIntent(intent, isColdStart = true)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (isShareIntent(intent)) {
            isLaunchedAsShareTarget = true
        }
        handleShareIntent(intent, isColdStart = false)
    }

    override fun onDestroy() {
        shareChannel = null
        for (request in pendingPayloadRequests) {
            try {
                request.result.error("ACTIVITY_DESTROYED", "Activity destroyed before payload resolved", null)
            } catch (_: Exception) {}
        }
        pendingPayloadRequests.clear()
        super.onDestroy()
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        healthConnectManager = HealthConnectManager(applicationContext)

        // Health Connect Channel
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, healthChannelName).setMethodCallHandler { call, result ->
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

        // Universal Share Sheet Receiver Channel
        val shareMethodChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, shareChannelName)
        shareChannel = shareMethodChannel

        shareMethodChannel.setMethodCallHandler { call, result ->
            when (call.method) {
                "getInitialSharedPayload" -> {
                    val shouldClear = call.argument<Boolean>("clear") ?: true
                    if (activeProcessingCount > 0) {
                        pendingPayloadRequests.add(PendingPayloadRequest(result, shouldClear))
                    } else {
                        val payload = pendingSharedPayload
                        if (shouldClear) {
                            pendingSharedPayload = null
                        }
                        result.success(payload)
                    }
                }
                "clearSharedPayload" -> {
                    pendingSharedPayload = null
                    result.success(null)
                }
                "clearStagingDirectory" -> {
                    lifecycleScope.launch(Dispatchers.IO) {
                        try {
                            val stagingDir = File(cacheDir, "shared_staging")
                            if (stagingDir.exists()) {
                                stagingDir.listFiles()?.forEach { it.deleteRecursively() }
                            } else {
                                stagingDir.mkdirs()
                            }
                            withContext(Dispatchers.Main) {
                                result.success(true)
                            }
                        } catch (e: Exception) {
                            withContext(Dispatchers.Main) {
                                result.error("CLEAR_STAGING_ERROR", e.message, null)
                            }
                        }
                    }
                }
                "isShareLaunch" -> {
                    result.success(isLaunchedAsShareTarget)
                }
                "showToast" -> {
                    val message = call.argument<String>("message") ?: ""
                    Toast.makeText(applicationContext, message, Toast.LENGTH_SHORT).show()
                    result.success(true)
                }
                "finishActivity" -> {
                    finish()
                    result.success(true)
                }
                "shareContent" -> {
                    val text = call.argument<String>("text")
                    if (text.isNullOrBlank()) {
                        result.error("INVALID_ARGUMENT", "text cannot be null or blank", null)
                        return@setMethodCallHandler
                    }
                    val title = call.argument<String>("title")
                    try {
                        val sendIntent = Intent().apply {
                            action = Intent.ACTION_SEND
                            putExtra(Intent.EXTRA_TEXT, text)
                            if (!title.isNullOrBlank()) {
                                putExtra(Intent.EXTRA_TITLE, title)
                                putExtra(Intent.EXTRA_SUBJECT, title)
                            }
                            type = "text/plain"
                        }
                        val shareIntent = Intent.createChooser(sendIntent, title)
                        startActivity(shareIntent)
                        result.success(true)
                    } catch (e: Exception) {
                        Log.e("MainActivity", "Failed to share content", e)
                        result.error("SHARE_ERROR", e.message, null)
                    }
                }
                "shareFile" -> {
                    val filePath = call.argument<String>("filePath")
                    if (filePath.isNullOrBlank()) {
                        result.error("INVALID_ARGUMENT", "filePath cannot be null or blank", null)
                        return@setMethodCallHandler
                    }
                    val file = File(filePath)
                    if (!file.exists()) {
                        result.error("FILE_NOT_FOUND", "File does not exist: $filePath", null)
                        return@setMethodCallHandler
                    }
                    val mimeTypeArg = call.argument<String>("mimeType")
                    val resolvedMime = if (!mimeTypeArg.isNullOrBlank()) {
                        mimeTypeArg
                    } else {
                        val ext = file.extension.lowercase()
                        val fromMap = MimeTypeMap.getSingleton().getMimeTypeFromExtension(ext)
                        fromMap ?: when (ext) {
                            "pdf" -> "application/pdf"
                            "txt" -> "text/plain"
                            "md" -> "text/markdown"
                            "json" -> "application/json"
                            "png" -> "image/png"
                            "jpg", "jpeg" -> "image/jpeg"
                            else -> "*/*"
                        }
                    }
                    try {
                        val contentUri: Uri = try {
                            FileProvider.getUriForFile(
                                applicationContext,
                                "${applicationContext.packageName}.fileprovider",
                                file
                            )
                        } catch (e: Exception) {
                            Log.w("MainActivity", "FileProvider failed for primary path, staging copy in cacheDir", e)
                            val stagingDir = File(cacheDir, "shared_staging")
                            if (!stagingDir.exists()) stagingDir.mkdirs()
                            val stagedCopy = File(stagingDir, file.name)
                            file.copyTo(stagedCopy, overwrite = true)
                            FileProvider.getUriForFile(
                                applicationContext,
                                "${applicationContext.packageName}.fileprovider",
                                stagedCopy
                            )
                        }

                        val sendIntent = Intent().apply {
                            action = Intent.ACTION_SEND
                            putExtra(Intent.EXTRA_STREAM, contentUri)
                            clipData = ClipData.newRawUri(file.name, contentUri)
                            type = resolvedMime
                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                        }
                        val shareIntent = Intent.createChooser(sendIntent, file.name).apply {
                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                        }
                        startActivity(shareIntent)
                        result.success(true)
                    } catch (e: Exception) {
                        Log.e("MainActivity", "Failed to share file", e)
                        result.error("SHARE_FILE_ERROR", e.message, null)
                    }
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
    }

    private fun isShareIntent(intent: Intent?): Boolean {
        if (intent == null) return false
        val action = intent.action
        return action == Intent.ACTION_SEND || action == Intent.ACTION_SEND_MULTIPLE
    }

    private fun handleShareIntent(intent: Intent?, isColdStart: Boolean) {
        if (!isShareIntent(intent)) return
        val currentIntent = intent ?: return

        activeProcessingCount++

        lifecycleScope.launch {
            try {
                val payload = withContext(Dispatchers.IO) {
                    extractSharePayload(currentIntent)
                }

                pendingSharedPayload = payload

                // Resolve any getInitialSharedPayload requests queued while extraction was active
                if (pendingPayloadRequests.isNotEmpty()) {
                    val requests = ArrayList(pendingPayloadRequests)
                    pendingPayloadRequests.clear()
                    var hasCleared = false
                    for (req in requests) {
                        try {
                            req.result.success(pendingSharedPayload)
                            if (req.shouldClear) {
                                hasCleared = true
                            }
                        } catch (e: Exception) {
                            Log.e("MainActivity", "Failed to deliver queued getInitialSharedPayload result", e)
                        }
                    }
                    if (hasCleared) {
                        pendingSharedPayload = null
                    }
                }

                // If warm resume (running application) and payload exists, notify Flutter via active event channel
                if (!isColdStart && payload != null) {
                    shareChannel?.invokeMethod("onShareReceived", payload)
                }
            } catch (e: Exception) {
                Log.e("MainActivity", "Failed to extract shared payload from intent", e)
                for (req in pendingPayloadRequests) {
                    try {
                        req.result.error("SHARE_EXTRACTION_ERROR", e.message, null)
                    } catch (_: Exception) {}
                }
                pendingPayloadRequests.clear()
            } finally {
                activeProcessingCount--
            }
        }
    }

    private fun extractSharePayload(intent: Intent): Map<String, Any?>? {
        val action = intent.action ?: return null
        val type = intent.type

        // Extract text strictly from extras or clipData (avoid treating file URI dataString as text)
        var text: String? = intent.getStringExtra(Intent.EXTRA_TEXT)
            ?: intent.getCharSequenceExtra(Intent.EXTRA_TEXT)?.toString()
            ?: intent.getStringArrayListExtra(Intent.EXTRA_TEXT)?.joinToString("\n")

        if (text.isNullOrBlank()) {
            val clipData = intent.clipData
            if (clipData != null) {
                val textBuilder = StringBuilder()
                for (i in 0 until clipData.itemCount) {
                    val clipText = clipData.getItemAt(i).text?.toString()
                    if (!clipText.isNullOrBlank()) {
                        if (textBuilder.isNotEmpty()) textBuilder.append("\n")
                        textBuilder.append(clipText)
                    }
                }
                if (textBuilder.isNotEmpty()) {
                    text = textBuilder.toString()
                }
            }
        }

        // Extract subject / title
        val subject = intent.getStringExtra(Intent.EXTRA_SUBJECT)
            ?: intent.getStringExtra(Intent.EXTRA_TITLE)

        // Extract stream / file URIs
        val uris = mutableListOf<Uri>()
        if (action == Intent.ACTION_SEND) {
            val streamUri: Uri? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
            } else {
                @Suppress("DEPRECATION")
                intent.getParcelableExtra(Intent.EXTRA_STREAM)
            }
            if (streamUri != null) {
                uris.add(streamUri)
            }
        } else if (action == Intent.ACTION_SEND_MULTIPLE) {
            val streamUris: ArrayList<Uri>? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri::class.java)
            } else {
                @Suppress("DEPRECATION")
                intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM)
            }
            if (streamUris != null) {
                uris.addAll(streamUris)
            }
        }

        // Fallback: check ClipData for URIs if EXTRA_STREAM did not yield any
        if (uris.isEmpty()) {
            val clipData = intent.clipData
            if (clipData != null) {
                for (i in 0 until clipData.itemCount) {
                    val clipUri = clipData.getItemAt(i).uri
                    if (clipUri != null) {
                        uris.add(clipUri)
                    }
                }
            }
        }

        // Fallback: check intent.data if still empty
        if (uris.isEmpty()) {
            intent.data?.let { uris.add(it) }
        }

        // Copy stream bytes into context.cacheDir/shared_staging/<filename>
        val stagedFiles = mutableListOf<Map<String, Any?>>()
        val stagingDir = File(cacheDir, "shared_staging")
        if (!stagingDir.exists()) {
            stagingDir.mkdirs()
        }

        val usedNamesInBatch = mutableSetOf<String>()
        for (uri in uris) {
            var destinationFile: File? = null
            try {
                val fileName = resolveFileName(uri, type)
                var candidate = File(stagingDir, fileName)

                // Collision disambiguation: check disk existence and batch collision
                if (candidate.exists() || usedNamesInBatch.contains(candidate.name)) {
                    val dotIndex = fileName.lastIndexOf('.')
                    val base = if (dotIndex != -1) fileName.substring(0, dotIndex) else fileName
                    val ext = if (dotIndex != -1) fileName.substring(dotIndex) else ""
                    var counter = 1
                    while (candidate.exists() || usedNamesInBatch.contains(candidate.name)) {
                        candidate = File(stagingDir, "${base}_$counter$ext")
                        counter++
                    }
                }
                destinationFile = candidate
                usedNamesInBatch.add(destinationFile.name)

                val inputStream = contentResolver.openInputStream(uri)
                if (inputStream != null) {
                    FileOutputStream(destinationFile).use { outputStream ->
                        inputStream.use { input ->
                            input.copyTo(outputStream)
                        }
                    }

                    if (destinationFile.exists() && destinationFile.length() > 0) {
                        val mimeType = try {
                            contentResolver.getType(uri)
                        } catch (_: Exception) {
                            null
                        } ?: type ?: "*/*"

                        stagedFiles.add(
                            mapOf(
                                "name" to destinationFile.name,
                                "path" to destinationFile.absolutePath,
                                "uri" to uri.toString(),
                                "mimeType" to mimeType,
                                "size" to destinationFile.length()
                            )
                        )
                    }
                } else {
                    Log.w("MainActivity", "contentResolver.openInputStream returned null for $uri")
                }
            } catch (e: Exception) {
                Log.e("MainActivity", "Failed to stage stream URI: $uri", e)
                destinationFile?.let {
                    if (it.exists()) {
                        it.delete()
                    }
                }
            }
        }

        val payload = mutableMapOf<String, Any?>()
        payload["action"] = action
        if (type != null) {
            payload["type"] = type
        }
        if (!text.isNullOrBlank()) {
            payload["text"] = text
        }
        if (!subject.isNullOrBlank()) {
            payload["subject"] = subject
        }
        if (stagedFiles.isNotEmpty()) {
            payload["files"] = stagedFiles
            payload["paths"] = stagedFiles.map { it["path"] as String }
            payload["path"] = stagedFiles[0]["path"]
            payload["fileName"] = stagedFiles[0]["name"]
        }

        return if (payload.isNotEmpty()) payload else null
    }

    private fun resolveFileName(uri: Uri, mimeType: String?): String {
        var name: String? = null
        val resolvedMimeType = try {
            contentResolver.getType(uri)
        } catch (_: Exception) {
            null
        } ?: mimeType

        if (uri.scheme == ContentResolver.SCHEME_CONTENT) {
            try {
                contentResolver.query(
                    uri,
                    arrayOf(OpenableColumns.DISPLAY_NAME),
                    null,
                    null,
                    null
                )?.use { cursor ->
                    if (cursor.moveToFirst()) {
                        val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                        if (nameIndex != -1) {
                            name = cursor.getString(nameIndex)
                        }
                    }
                }
            } catch (e: Exception) {
                Log.w("MainActivity", "Failed to resolve DISPLAY_NAME for: $uri", e)
            }
        }

        if (name.isNullOrBlank()) {
            name = uri.lastPathSegment
        }

        val fallbackExt = getExtensionFromMimeType(resolvedMimeType)

        if (name.isNullOrBlank()) {
            name = "shared_${System.currentTimeMillis()}$fallbackExt"
        }

        // Sanitize: strip illegal characters and prevent directory traversal
        var sanitized = File(name).name.replace(Regex("[\\\\/:*?\"<>|]"), "_").trim()
        if (sanitized == "." || sanitized == ".." || sanitized.isBlank()) {
            sanitized = "shared_${System.currentTimeMillis()}$fallbackExt"
        }

        // If the filename does not contain an extension, append the MIME-derived extension
        if (!sanitized.contains('.') && fallbackExt.isNotBlank()) {
            sanitized += fallbackExt
        }

        return sanitized
    }

    private fun getExtensionFromMimeType(mimeType: String?): String {
        if (mimeType.isNullOrBlank()) return ""
        val cleanMime = mimeType.lowercase().split(";")[0].trim()

        // Comprehensive audio, image, and document MIME extension mappings
        val explicitExt = when (cleanMime) {
            "audio/mp4", "audio/m4a" -> ".m4a"
            "audio/mpeg", "audio/mp3" -> ".mp3"
            "audio/wav", "audio/x-wav" -> ".wav"
            "audio/aac" -> ".aac"
            "audio/ogg", "audio/opus" -> ".opus"
            "audio/flac" -> ".flac"
            "image/jpeg", "image/jpg" -> ".jpg"
            "image/png" -> ".png"
            "image/webp" -> ".webp"
            "image/gif" -> ".gif"
            "application/pdf" -> ".pdf"
            "text/plain" -> ".txt"
            "text/markdown", "text/x-markdown" -> ".md"
            "text/csv" -> ".csv"
            "text/html" -> ".html"
            "application/json" -> ".json"
            "application/zip" -> ".zip"
            "application/octet-stream" -> ""
            else -> null
        }
        if (explicitExt != null) {
            return explicitExt
        }

        val extFromMap = try {
            MimeTypeMap.getSingleton().getExtensionFromMimeType(cleanMime)
        } catch (_: Exception) {
            null
        }
        if (!extFromMap.isNullOrBlank()) {
            return ".$extFromMap"
        }
        return ""
    }
}
