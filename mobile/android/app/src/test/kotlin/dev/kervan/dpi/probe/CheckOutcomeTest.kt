package dev.kervan.dpi.probe

import java.net.SocketException
import java.net.SocketTimeoutException
import java.net.URL
import java.net.UnknownHostException
import java.security.cert.CertificateExpiredException
import javax.net.ssl.SSLException
import javax.net.ssl.SSLHandshakeException
import javax.net.ssl.SSLPeerUnverifiedException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Feeds the decision the answers a censored or captive network gives. */
class CheckOutcomeTest {
  private val custom = AccessTarget.custom("https://example.org/page")!!
  private val all = AccessTarget.BUILT_IN + custom
  private val replies = mapOf(
    "wikipedia" to (200 to """{"batchcomplete":"","query":{"general":{"mainpage":"Main Page","sitename":"Wikipedia"}}}"""),
    "google" to (204 to ""),
    "cloudflare" to (200 to "fl=1f1\nh=www.cloudflare.com\nip=192.0.2.1\ncolo=AMS\n"),
    "apple" to (200 to "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>\n"),
  )
  private val blockPage = "<html><body>Bu siteye erişim mahkeme kararıyla engellenmiştir.</body></html>"

  private fun outcome(t: AccessTarget, status: Int, body: String, at: String = t.url) =
    CheckOutcome.of(t, URL(at), status, body)

  private fun own(t: AccessTarget) = replies[t.key] ?: (200 to "")

  @Test
  fun everyBuiltInTargetAcceptsItsOwnReply() {
    for (t in AccessTarget.BUILT_IN) assertEquals(t.key, CheckOutcome.VERIFIED, outcome(t, own(t).first, own(t).second))
  }

  @Test
  fun customTargetIsAtMostAnswered() {
    assertEquals(CheckOutcome.ANSWERED, outcome(custom, 200, "anything"))
  }

  @Test
  fun blockPageWithHttp200IsNeverOk() {
    for (t in AccessTarget.BUILT_IN) {
      assertFalse(t.key, outcome(t, 200, blockPage).ok)
      assertFalse(t.key, outcome(t, 200, "").ok)
    }
  }

  @Test
  fun anotherTargetsReplyIsNeverOk() {
    for (t in AccessTarget.BUILT_IN) for ((key, reply) in replies) {
      if (key != t.key) assertFalse("${t.key} took $key", outcome(t, reply.first, reply.second).ok)
    }
  }

  @Test
  fun anotherAddressIsNeverOk() {
    for (t in all) for (at in listOf(
      "https://login.hotspot.example/portal", "https://${t.host}.attacker.example/",
      "http://${t.host}/", "https://${t.host}:8443/",
    )) {
      assertEquals(at, CheckOutcome.OTHER_REPLY, outcome(t, own(t).first, own(t).second, at))
    }
  }

  @Test
  fun redirectsAndOtherStatusesAreNeverOk() {
    for (t in all) {
      for (s in listOf(301, 302, 303, 307, 308)) assertEquals(CheckOutcome.REDIRECTED, outcome(t, s, own(t).second))
      for (s in listOf(200, 204, 403, 404, 429, 451, 500, 503, 511)) {
        if (s != own(t).first) assertEquals("${t.key} $s", CheckOutcome.OTHER_STATUS, outcome(t, s, own(t).second))
      }
    }
  }

  @Test
  fun nearMissBodiesAreNeverOk() {
    for ((t, body) in listOf(
      AccessTarget.WIKIPEDIA to """{"query":{"general":{"sitename":"Portal"}}}""",
      AccessTarget.WIKIPEDIA to """{"query":[]}""",
      AccessTarget.WIKIPEDIA to "<title>Wikipedia</title>",
      AccessTarget.CLOUDFLARE to "h=www.cloudflare.com.attacker.example\ncolo=AMS\n",
      AccessTarget.APPLE to "<HTML><BODY>Success</BODY></HTML>",
    )) assertEquals(body, CheckOutcome.OTHER_REPLY, outcome(t, 200, body))
    assertEquals(CheckOutcome.OTHER_REPLY, outcome(AccessTarget.GOOGLE, 204, "x"))
  }

  @Test
  fun transportErrorsAreDistinguished() {
    val untrusted = SSLHandshakeException("x").apply { initCause(CertificateExpiredException()) }
    assertEquals(CheckOutcome.UNTRUSTED, CheckOutcome.of(untrusted))
    assertEquals(CheckOutcome.UNTRUSTED, CheckOutcome.of(SSLPeerUnverifiedException("Hostname not verified")))
    assertEquals(CheckOutcome.NAME_NOT_RESOLVED, CheckOutcome.of(UnknownHostException("x")))
    for (e in listOf(SocketException("Connection reset"), SocketTimeoutException(), SSLException("reset"), SSLHandshakeException("closed"))) {
      assertEquals(e.toString(), CheckOutcome.NO_ANSWER, CheckOutcome.of(e))
    }
  }

  @Test
  fun onlyVerifiedAndAnsweredAreOk() {
    assertEquals(setOf(CheckOutcome.VERIFIED, CheckOutcome.ANSWERED), CheckOutcome.entries.filter { it.ok }.toSet())
    assertTrue(CheckOutcome.entries.none { "BYPASS" in it.name })
  }
}
