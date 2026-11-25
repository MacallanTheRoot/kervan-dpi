package dev.kervan.dpi.engine

import dev.kervan.dpi.probe.CheckOutcome
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class EngineModelTest {

  @Test
  fun nativeCodesMapToPhases() {
    assertEquals(EnginePhase.STOPPED, EnginePhase.fromNative(0))
    assertEquals(EnginePhase.STARTING, EnginePhase.fromNative(1))
    assertEquals(EnginePhase.RUNNING, EnginePhase.fromNative(2))
    assertEquals(EnginePhase.STOPPING, EnginePhase.fromNative(3))
    assertEquals(EnginePhase.FAILED, EnginePhase.fromNative(4))
    assertEquals(EnginePhase.FAILED, EnginePhase.fromNative(99))
  }

  @Test
  fun controlsFollowPhase() {
    val stopped = EngineUiState(phase = EnginePhase.STOPPED)
    assertTrue(stopped.canEnable)
    assertFalse(stopped.canDisable)
    assertFalse(stopped.settingsLocked)

    val running = EngineUiState(phase = EnginePhase.RUNNING)
    assertFalse(running.canEnable)
    assertTrue(running.canDisable)
    assertTrue(running.settingsLocked)

    for (busy in listOf(EnginePhase.STARTING, EnginePhase.STOPPING)) {
      val s = EngineUiState(phase = busy)
      assertFalse(s.canEnable)
      assertFalse(s.canDisable)
      assertTrue(s.settingsLocked)
    }

    val failed = EngineUiState(phase = EnginePhase.FAILED, error = "x")
    assertTrue("failure must be retryable", failed.canEnable)
    assertFalse(failed.canDisable)
  }

  @Test
  fun runningIsNeverReportedAsBypassProof() {
    assertFalse(EngineUiState(phase = EnginePhase.RUNNING).bypassVerified)
  }

  @Test
  fun reconnectIsNeededOnlyWhenRunningWithADifferentConfig() {
    val a = EngineConfig("-d1", DnsProvider.CLOUDFLARE)
    val b = EngineConfig("-d1", DnsProvider.GOOGLE)
    val running = EngineUiState(phase = EnginePhase.RUNNING, activeConfig = a)
    assertFalse(running.needsReconnect(a))
    assertTrue(running.needsReconnect(b))
    assertFalse("invalid selection never prompts a reconnect", running.needsReconnect(null))
    assertFalse(EngineUiState(phase = EnginePhase.STOPPED).needsReconnect(b))
  }

  @Test
  fun logIsBounded() {
    var s = EngineUiState()
    repeat(EngineUiState.MAX_LOG + 25) { s = s.withLog("line $it") }
    assertEquals(EngineUiState.MAX_LOG, s.log.size)
    assertEquals("line ${EngineUiState.MAX_LOG + 24}", s.log.last())
  }

  @Test
  fun defaultStrategyIsAccepted() {
    assertNull(DesyncArgs.validate(DesyncArgs.DEFAULT))
  }

  @Test
  fun engineOwnedOptionsAreRejected() {
    for (bad in listOf(
      "-i 0.0.0.0", "--ip 0.0.0.0", "-p 1080", "--port=1080", "-P /tmp/x",
      "--protect-path /tmp/x", "-U", "--no-udp", "-D", "-w f", "-E", "--transparent",
      "-s1 -i0.0.0.0", "-ip",
    )) {
      assertNotNull("should reject: $bad", DesyncArgs.validate(bad))
    }
  }

  @Test
  fun unsafeTextIsRejected() {
    assertNotNull(DesyncArgs.validate("-s1\u0000"))
    assertNotNull(DesyncArgs.validate("-s1 ; rm -rf /"))
    assertNotNull(DesyncArgs.validate("x".repeat(DesyncArgs.MAX_LENGTH + 1)))
    assertNotNull(DesyncArgs.validate((1..100).joinToString(" ") { "-s$it" }))
  }

  @Test
  fun ordinaryStrategiesPass() {
    for (ok in listOf("", "-s1", "-d1 -s1+s", "-o1 -At,r,s -d1", "--disorder 1 --split 1+s", "-f-1 -t5")) {
      assertNull("should accept: $ok", DesyncArgs.validate(ok))
    }
  }

  @Test
  fun checkResultIsKeptOnlyForTheStateItWasMadeIn() {
    val check = AccessCheck("example.org", CheckOutcome.VERIFIED, engineOn = true, time = "12:00")
    val running = EngineUiState(phase = EnginePhase.RUNNING)
    assertEquals(check, running.withCheck(check, running.checkEpoch).accessCheck)
    // Restarted, or another target chosen, while the check was in flight.
    val restarted = running.withoutCheck().withoutCheck()
    assertNull(restarted.withCheck(check, running.checkEpoch).accessCheck)
    assertNull(running.withCheck(check, 0).withoutCheck().accessCheck)
  }

  @Test
  fun checksNeedASettledEngine() {
    for (p in EnginePhase.entries) {
      assertEquals(p.name, p != EnginePhase.STARTING && p != EnginePhase.STOPPING, EngineUiState(phase = p).settled)
    }
  }
}
