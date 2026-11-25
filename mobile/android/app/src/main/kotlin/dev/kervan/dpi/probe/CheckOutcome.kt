package dev.kervan.dpi.probe

import java.net.URL
import java.net.UnknownHostException
import java.security.cert.CertificateException
import javax.net.ssl.SSLPeerUnverifiedException

/**
 * What one check showed. "Bypass verified" is deliberately not an outcome: it needs the
 * same check to fail with Kervan off on the same network.
 */
enum class CheckOutcome(val ok: Boolean) {
  /** Trusted TLS, no redirect, and the reply this built-in target is known to give. */
  VERIFIED(true),
  /** A custom address returned HTTP 200 over trusted TLS. Its content cannot be checked. */
  ANSWERED(true),
  /** A redirect, which is never followed. Captive portals and block pages do this. */
  REDIRECTED(false),
  /** Another HTTP status than the target gives. */
  OTHER_STATUS(false),
  /** Another address or another body than the target's own. */
  OTHER_REPLY(false),
  /** The certificate is not trusted or not for this host; the answer was rejected. */
  UNTRUSTED(false),
  NAME_NOT_RESOLVED(false),
  /** Reset, timeout or any other failure before an HTTP answer. */
  NO_ANSWER(false);

  companion object {
    /** The whole decision, without the network, so tests can feed it block pages. */
    fun of(target: AccessTarget, answeredUrl: URL, status: Int, body: String): CheckOutcome {
      val sameAddress = answeredUrl.protocol == "https" &&
        (answeredUrl.port == -1 || answeredUrl.port == 443) &&
        answeredUrl.host.equals(target.host, ignoreCase = true)
      if (!sameAddress) return OTHER_REPLY
      if (status in 300..399) return REDIRECTED
      val expected = if (target.reply == AccessTarget.Reply.EMPTY_204) 204 else 200
      if (status != expected) return OTHER_STATUS
      return when (target.reply) {
        AccessTarget.Reply.UNKNOWN -> ANSWERED
        AccessTarget.Reply.EMPTY_204 -> verifiedIf(body.isEmpty())
        AccessTarget.Reply.WIKIPEDIA -> verifiedIf(body.trimStart().startsWith('{') && siteInfo.containsMatchIn(body))
        AccessTarget.Reply.CLOUDFLARE_TRACE -> {
          val lines = body.lines()
          verifiedIf("h=${target.host}" in lines && lines.any { it.startsWith("colo=") })
        }
        AccessTarget.Reply.APPLE_SUCCESS ->
          verifiedIf(body.trim() == "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>")
      }
    }

    fun of(error: Exception): CheckOutcome {
      val causes = generateSequence<Throwable>(error) { it.cause }.take(10).toList()
      return when {
        causes.any { it is CertificateException || it is SSLPeerUnverifiedException } -> UNTRUSTED
        causes.any { it is UnknownHostException } -> NAME_NOT_RESOLVED
        else -> NO_ANSWER
      }
    }

    private fun verifiedIf(matches: Boolean) = if (matches) VERIFIED else OTHER_REPLY

    /** The site info fields, in a JSON object; a page that merely mentions Wikipedia has neither. */
    private val siteInfo = Regex("\"query\"\\s*:\\s*\\{\\s*\"general\"\\s*:\\s*\\{[^{}]*\"sitename\"\\s*:\\s*\"Wikipedia\"")
  }
}
