package dev.kervan.dpi.engine

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class EngineSettingsTest {

  @Test
  fun defaultsReproduceTheVerifiedStrategy() {
    val config = EngineSettings().toConfig()
    assertEquals(DesyncArgs.DEFAULT, config.desyncArgs)
    assertEquals(DnsProvider.CLOUDFLARE, config.dns)
  }

  @Test
  fun basicModeIgnoresAdvancedValues() {
    val s = EngineSettings(
      advanced = false, disorder = false, splitAtSni = false, oob = true,
      customArgs = "-f-1", dns = DnsProvider.QUAD9,
    )
    assertEquals(EngineConfig(DesyncArgs.DEFAULT, DnsProvider.CLOUDFLARE), s.toConfig())
  }

  @Test
  fun advancedTogglesBuildArgsInFixedOrder() {
    val s = EngineSettings(advanced = true, disorder = true, splitAtSni = false, tlsRecordAtSni = true, oob = true)
    assertEquals("-d1 -r1+s -o1", s.toConfig().desyncArgs)
  }

  @Test
  fun noMethodSelectedMeansPlainRelay() {
    val s = EngineSettings(advanced = true, disorder = false, splitAtSni = false, tlsRecordAtSni = false, oob = false)
    assertEquals("", s.toConfig().desyncArgs)
    assertTrue(s.relayOnly)
  }

  @Test
  fun customArgumentsOverrideToggles() {
    val s = EngineSettings(advanced = true, customArgs = "  -o1 -At,r,s -d1  ")
    assertEquals("-o1 -At,r,s -d1", s.toConfig().desyncArgs)
  }

  @Test
  fun invalidCustomArgumentsAreReportedAndNeverApplied() {
    val s = EngineSettings(advanced = true, customArgs = "-i 0.0.0.0")
    assertNotNull(s.error())
    assertNull(s.toConfigOrNull())
  }

  @Test
  fun advancedDnsIsApplied() {
    assertEquals(DnsProvider.GOOGLE, EngineSettings(advanced = true, dns = DnsProvider.GOOGLE).toConfig().dns)
  }

  @Test
  fun dnsProviderRoundTripsByStableKeyAndFallsBackSafely() {
    for (p in DnsProvider.entries) assertEquals(p, DnsProvider.fromKey(p.key))
    assertEquals(DnsProvider.CLOUDFLARE, DnsProvider.fromKey("garbage"))
    assertEquals(DnsProvider.CLOUDFLARE, DnsProvider.fromKey(null))
  }

  @Test
  fun resetRestoresDefaults() {
    val changed = EngineSettings(advanced = true, oob = true, customArgs = "-s2", dns = DnsProvider.QUAD9)
    assertEquals(EngineSettings(), changed.reset())
  }
}
