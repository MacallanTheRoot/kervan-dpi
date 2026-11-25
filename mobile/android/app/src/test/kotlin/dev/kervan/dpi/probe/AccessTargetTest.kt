package dev.kervan.dpi.probe

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AccessTargetTest {

  @Test
  fun builtInTargetsAreDistinctHttpsAndNotDiscord() {
    assertEquals(listOf("wikipedia", "google", "cloudflare", "apple"), AccessTarget.BUILT_IN.map { it.key })
    for (t in AccessTarget.BUILT_IN) {
      assertTrue(t.key, t.url.startsWith("https://"))
      assertNotEquals(t.key, AccessTarget.Reply.UNKNOWN, t.reply)
      assertFalse(t.key, "discord" in t.url)
    }
  }

  @Test
  fun customAcceptsPublicHttps() {
    val accepted = mapOf(
      "https://example.org" to "https://example.org",
      "example.org" to "https://example.org",
      "  https://example.org/path?q=1  " to "https://example.org/path?q=1",
      "HTTPS://Example.ORG/" to "https://example.org/",
      "https://example.org:443/" to "https://example.org/",
      "https://example.org/a#secret" to "https://example.org/a",
      "https://xn--trkiye-3ya.example/%20" to "https://xn--trkiye-3ya.example/%20",
    )
    for ((text, url) in accepted) {
      val t = AccessTarget.custom(text)
      assertEquals(text, url, t?.url)
      assertEquals(text, AccessTarget.Reply.UNKNOWN, t?.reply)
    }
  }

  @Test
  fun customRejectsEverythingElse() {
    for (text in listOf(
      "", "   ", "http://example.org", "ftp://example.org", "file:///etc/passwd", "javascript://example.org",
      "content://example.org/x", "https://", "https://user:pw@example.org", "https://user@example.org", "https://@example.org",
      "https://example.org:8443", "https://192.168.1.1", "https://1.1.1.1/", "https://[::1]/", "https://localhost",
      "https://router", "https://nas.local", "https://host.internal", "https://2130706433", "https://example.org.",
      "https://-bad.org", "https://exa mple.org", "https://0x7f.0x1", "https://under_score.org",
      "https://example.org\\@evil.example", "https://example.org\r\nHost: x", "a".repeat(3000) + ".org",
    )) {
      assertNull(text, AccessTarget.custom(text))
    }
  }

  @Test
  fun logsNeverContainACustomPath() {
    val t = AccessTarget.custom("https://example.org/private?token=abc")!!
    val line = ConnectivityProbe.format(
      ConnectivityProbe.Result(t, "192.0.2.1", CheckOutcome.ANSWERED, "HTTP 200, TLS X", 200),
    )
    assertEquals("probe https://example.org/ [192.0.2.1] -> OK: HTTP 200, TLS X (ANSWERED)", line)
  }

  @Test
  fun builtInEvidenceLineKeepsItsShape() {
    val line = ConnectivityProbe.format(
      ConnectivityProbe.Result(AccessTarget.GOOGLE, "-", CheckOutcome.NO_ANSWER, "SocketException: Connection reset"),
    )
    assertEquals(
      "probe https://www.gstatic.com/generate_204 [-] -> FAIL: SocketException: Connection reset (NO_ANSWER)", line,
    )
  }

  @Test
  fun settingsDefaultRestoreAndValidate() {
    assertEquals(AccessTarget.WIKIPEDIA, CheckSettings().target)
    assertEquals(AccessTarget.WIKIPEDIA, CheckSettings.restore("discord", null).target)
    assertEquals(AccessTarget.WIKIPEDIA, CheckSettings.restore(null, null).target)
    assertEquals(AccessTarget.APPLE, CheckSettings.restore("apple", "x").target)
    assertEquals("example.org", CheckSettings.restore("custom", "https://example.org").target?.host)
    assertNull(CheckSettings.restore("custom", "http://example.org").target)
  }
}
