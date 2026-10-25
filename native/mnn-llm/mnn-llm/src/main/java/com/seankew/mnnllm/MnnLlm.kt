package com.seankew.mnnllm

import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.asCoroutineDispatcher
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.concurrent.Executors

data class ChatMsg(val role: String, val content: String)

fun interface TokenCallback {
    /** Return false to stop generation. JNI calls this as onToken([B)Z. */
    fun onToken(bytes: ByteArray): Boolean
}

/**
 * Thin native wrapper. Load/generate/release are serialized on one worker thread.
 * The matching MNN shared libraries and headers must be built from the same revision.
 */
class MnnLlm : AutoCloseable {
    companion object {
        init {
            System.loadLibrary("MNN")
            System.loadLibrary("MNN_Express")
            System.loadLibrary("llm")
            System.loadLibrary("mnn_llm_jni")
        }

        fun defaultConfig(threads: Int = 4): String = """
            {
              "backend_type": "cpu",
              "thread_num": $threads,
              "precision": "low",
              "memory": "low",
              "sampler_type": "mixed",
              "temperature": 0.7,
              "topP": 0.9,
              "topK": 40
            }
        """.trimIndent()
    }

    private val executor = Executors.newSingleThreadExecutor { r ->
        Thread(r, "mnn-llm").apply { priority = Thread.NORM_PRIORITY }
    }
    private val dispatcher: CoroutineDispatcher = executor.asCoroutineDispatcher()

    @Volatile private var handle: Long = 0L
    val isLoaded: Boolean get() = handle != 0L

    private external fun nativeCreate(configPath: String, extraConfig: String): Long
    private external fun nativeGenerate(
        handle: Long,
        roles: Array<String>,
        contents: Array<ByteArray>,
        maxNewTokens: Int,
        callback: TokenCallback
    ): Int
    private external fun nativeStop(handle: Long)
    private external fun nativeReset(handle: Long)
    private external fun nativeRelease(handle: Long)

    /** modelDir must contain config.json and all files required by this MNN model export. */
    suspend fun load(modelDir: File, config: String = defaultConfig()) = withContext(dispatcher) {
        require(File(modelDir, "config.json").isFile) {
            "Missing model config: ${File(modelDir, "config.json").absolutePath}"
        }
        if (handle != 0L) return@withContext
        val created = nativeCreate(File(modelDir, "config.json").absolutePath, config)
        check(created != 0L) { "MNN model load failed; inspect logcat for MnnLlmJNI." }
        handle = created
    }

    /** Emits decoded UTF-8 chunks. Cancelling collection requests native generation stop. */
    fun chat(messages: List<ChatMsg>, maxNewTokens: Int = 512): Flow<String> = callbackFlow {
        val h = handle
        check(h != 0L) { "MNN model is not loaded." }
        require(maxNewTokens > 0) { "maxNewTokens must be positive." }

        val callback = TokenCallback { bytes ->
            trySend(String(bytes, Charsets.UTF_8)).isSuccess
        }
        val job = launch(dispatcher) {
            try {
                val result = nativeGenerate(
                    h,
                    messages.map(ChatMsg::role).toTypedArray(),
                    messages.map { it.content.toByteArray(Charsets.UTF_8) }.toTypedArray(),
                    maxNewTokens,
                    callback
                )
                if (result < 0) close(IllegalStateException("nativeGenerate failed: $result"))
                else close()
            } catch (t: Throwable) {
                close(t)
            }
        }

        awaitClose {
            if (job.isActive && handle == h) nativeStop(h)
        }
    }

    fun stop() {
        val h = handle
        if (h != 0L) nativeStop(h)
    }

    suspend fun reset() = withContext(dispatcher) {
        val h = handle
        if (h != 0L) nativeReset(h)
    }

    override fun close() {
        val h = handle
        handle = 0L
        if (h != 0L) {
            nativeStop(h)
            executor.execute { nativeRelease(h); executor.shutdown() }
        } else {
            executor.shutdown()
        }
    }
}
