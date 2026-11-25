package dev.kervan.dpi.probe

import java.net.URI
import java.net.URISyntaxException
import java.util.Locale

/** One address the connection check can ask, and how to recognise its real reply. */
data class AccessTarget(val key: String, val label: String, val url: String, val reply: Reply) {

  enum class Reply {
    /** Wikipedia site info: JSON naming the site. */
    WIKIPEDIA,
    /** HTTP 204 with an empty body. */
    EMPTY_204,
    /** Cloudflare trace: text lines, one of them `h=<host>`. */
    CLOUDFLARE_TRACE,
    /** Apple's connectivity test page. */
    APPLE_SUCCESS,
    /** A custom address: the app cannot know what the real page looks like. */
    UNKNOWN,
  }

  val host: String get() = URI(url).host

  /** For logs and diagnostics: a custom address's path may be private. */
  val logUrl: String get() = if (reply == Reply.UNKNOWN) "https://$host/" else url

  companion object {
    const val CUSTOM_KEY = "custom"
    private const val MAX_LENGTH = 2048
    private val label = Regex("[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?")
    private val localNames = setOf("local", "localhost", "internal", "lan", "home", "arpa")

    val WIKIPEDIA = AccessTarget(
      "wikipedia", "Wikipedia",
      "https://en.wikipedia.org/w/api.php?action=query&meta=siteinfo&siprop=general&format=json", Reply.WIKIPEDIA,
    )
    val GOOGLE = AccessTarget("google", "Google", "https://www.gstatic.com/generate_204", Reply.EMPTY_204)
    val CLOUDFLARE = AccessTarget(
      "cloudflare", "Cloudflare", "https://www.cloudflare.com/cdn-cgi/trace", Reply.CLOUDFLARE_TRACE,
    )
    val APPLE = AccessTarget("apple", "Apple", "https://www.apple.com/library/test/success.html", Reply.APPLE_SUCCESS)

    /** The first one is the default. */
    val BUILT_IN = listOf(WIKIPEDIA, GOOGLE, CLOUDFLARE, APPLE)

    /**
     * A custom target, or null unless [text] is a plain public HTTPS address: no other
     * scheme, no credentials, no other port, no IP address and no local name. A missing
     * scheme means https.
     */
    fun custom(text: String): AccessTarget? {
      val trimmed = text.trim()
      if (trimmed.isEmpty() || trimmed.length > MAX_LENGTH) return null
      val uri = try {
        URI(if ("://" in trimmed) trimmed else "https://$trimmed")
      } catch (_: URISyntaxException) {
        return null
      }
      val host = uri.host?.lowercase(Locale.ROOT) ?: return null
      if (!uri.scheme.equals("https", ignoreCase = true) || uri.rawUserInfo != null) return null
      if (uri.port != -1 && uri.port != 443) return null
      if (!isPublicName(host)) return null
      val path = uri.rawPath.orEmpty() + (uri.rawQuery?.let { "?$it" } ?: "")
      // Rebuilt without the fragment; non-ASCII path characters are percent-encoded.
      val url = URI("https://$host$path").toASCIIString()
      return AccessTarget(CUSTOM_KEY, host, url, Reply.UNKNOWN)
    }

    private fun isPublicName(host: String): Boolean {
      val labels = host.split('.')
      if (host.length > 253 || labels.size < 2 || !labels.all(label::matches)) return false
      // A last label that starts with a digit is an IPv4 address, not a name.
      return !labels.last()[0].isDigit() && labels.last() !in localNames
    }
  }
}

/** What the user selected; persisted by CheckStore. */
data class CheckSettings(val key: String = AccessTarget.BUILT_IN[0].key, val customText: String = "") {
  /** Null while the custom address is not acceptable. */
  val target: AccessTarget?
    get() = if (key == AccessTarget.CUSTOM_KEY) AccessTarget.custom(customText) else AccessTarget.BUILT_IN.firstOrNull { it.key == key }

  companion object {
    /** Unknown saved values fall back to the default target. */
    fun restore(key: String?, customText: String?): CheckSettings {
      val known = key == AccessTarget.CUSTOM_KEY || AccessTarget.BUILT_IN.any { it.key == key }
      return CheckSettings(if (known) key!! else AccessTarget.BUILT_IN[0].key, customText.orEmpty())
    }
  }
}
