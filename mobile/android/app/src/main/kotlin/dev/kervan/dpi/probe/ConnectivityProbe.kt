package dev.kervan.dpi.probe

import java.io.ByteArrayOutputStream
import java.net.InetAddress
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import javax.net.ssl.HttpsURLConnection

/**
 * Evidence collector: performs a real HTTPS request from this app's process.
 * The app is NOT excluded from its own VPN, so while the engine runs the
 * request travels through the tunnel exactly like other apps' traffic.
 * A result is a fact about this network at this moment, nothing more.
 */
object ConnectivityProbe {
  /** More than any built-in reply needs. A longer body is cut here. */
  private const val MAX_BODY = 64 * 1024
  private const val TOTAL_SECONDS = 20L
  private val watchdog = Executors.newSingleThreadScheduledExecutor { r ->
    Thread(r, "kervan-probe-watchdog").apply { isDaemon = true }
  }

  /** [detail] is the technical evidence line (HTTP code and cipher, or the exception). */
  data class Result(
    val target: AccessTarget,
    val resolved: String,
    val outcome: CheckOutcome,
    val detail: String,
    val status: Int? = null,
  )

  fun probe(target: AccessTarget, timeoutMs: Int = 10_000): Result {
    val resolved = try {
      InetAddress.getAllByName(target.host).take(2).joinToString(",") { it.hostAddress ?: "?" }
    } catch (e: Exception) {
      return Result(target, "-", CheckOutcome.NAME_NOT_RESOLVED, "DNS failed: ${describe(e)}")
    }
    return try {
      val conn = (URL(target.url).openConnection() as HttpsURLConnection).apply {
        connectTimeout = timeoutMs
        readTimeout = timeoutMs
        instanceFollowRedirects = false
        useCaches = false
        requestMethod = "GET"
        setRequestProperty("User-Agent", "KervanDPI-probe")
        // Never reuse a connection opened before Kervan was turned on or off.
        setRequestProperty("Connection", "close")
      }
      // A reply that trickles in must not run past the read timeout forever.
      val cutOff = watchdog.schedule({ conn.disconnect() }, TOTAL_SECONDS, TimeUnit.SECONDS)
      try {
        val code = conn.responseCode
        val cipher = conn.cipherSuite
        val body = if (code == 200) readBody(conn) else ""
        Result(target, resolved, CheckOutcome.of(target, conn.url, code, body), "HTTP $code, TLS $cipher", code)
      } finally {
        cutOff.cancel(false)
        conn.disconnect()
      }
    } catch (e: Exception) {
      Result(target, resolved, CheckOutcome.of(e), describe(e))
    }
  }

  private fun readBody(conn: HttpsURLConnection): String = conn.inputStream.use { input ->
    val out = ByteArrayOutputStream()
    val buffer = ByteArray(8192)
    while (out.size() < MAX_BODY) {
      val n = input.read(buffer, 0, minOf(buffer.size, MAX_BODY - out.size()))
      if (n < 0) break
      out.write(buffer, 0, n)
    }
    out.toString(Charsets.UTF_8.name())
  }

  private fun describe(e: Exception) = "${e.javaClass.simpleName}: ${e.message}"

  fun format(r: Result) =
    "probe ${r.target.logUrl} [${r.resolved}] -> ${if (r.outcome.ok) "OK" else "FAIL"}: ${r.detail} (${r.outcome.name})"
}
