package dev.kervan.dpi.engine

import dev.kervan.dpi.probe.CheckOutcome

/** Mirrors kv_state_t in mobile/core/include/kervan_engine.h. */
enum class EnginePhase {
  STOPPED, STARTING, RUNNING, STOPPING, FAILED;

  companion object {
    fun fromNative(code: Int): EnginePhase = when (code) {
      0 -> STOPPED
      1 -> STARTING
      2 -> RUNNING
      3 -> STOPPING
      else -> FAILED
    }
  }
}

/** One snapshot drives every control; the UI never infers state from widgets. */
data class EngineUiState(
  val phase: EnginePhase = EnginePhase.STOPPED,
  val error: String? = null,
  val log: List<String> = emptyList(),
  /** Config the running engine was started with; null when not running. */
  val activeConfig: EngineConfig? = null,
  /** Result of the last connection check in the current engine state; null if none. */
  val accessCheck: AccessCheck? = null,
  /** Moves on every phase or target change, so a check still in flight can be recognised as stale. */
  val checkEpoch: Int = 0,
) {
  val canEnable get() = phase == EnginePhase.STOPPED || phase == EnginePhase.FAILED
  val canDisable get() = phase == EnginePhase.RUNNING
  val settingsLocked get() = phase == EnginePhase.STARTING || phase == EnginePhase.RUNNING ||
    phase == EnginePhase.STOPPING

  /** The engine can only say traffic is flowing through it, never that DPI was bypassed. */
  val bypassVerified get() = false

  /** False while starting or stopping: a check would belong to neither state. */
  val settled get() = phase != EnginePhase.STARTING && phase != EnginePhase.STOPPING

  /** Drops the check result, and any check still in flight. */
  fun withoutCheck() = copy(accessCheck = null, checkEpoch = checkEpoch + 1)

  /** Keeps [check] only if neither the engine nor the target changed since [epoch]. */
  fun withCheck(check: AccessCheck, epoch: Int) = if (epoch == checkEpoch) copy(accessCheck = check) else this

  /** True when the engine runs with a different config than the one now selected. */
  fun needsReconnect(selected: EngineConfig?): Boolean =
    phase == EnginePhase.RUNNING && activeConfig != null && selected != null && selected != activeConfig

  fun withLog(line: String): EngineUiState = copy(log = (log + line).takeLast(MAX_LOG))

  companion object {
    const val MAX_LOG = 200
  }
}

/**
 * User-editable ByeDPI strategy. The engine itself sets the listen address, port,
 * protect path and UDP mode; those options are rejected here so a strategy can
 * never expose the proxy beyond loopback or disable socket protection.
 */
object DesyncArgs {
  /** Starting point only: split/disorder at the TLS SNI. Not verified against any ISP. */
  const val DEFAULT = "-d1 -s1+s -r1+s"
  const val MAX_LENGTH = 512
  private const val MAX_TOKENS = 80
  private val allowed = Regex("[A-Za-z0-9 +\\-=,.:_*?#]*")
  private val forbiddenShort = setOf('i', 'p', 'P', 'U', 'D', 'w', 'E')
  private val forbiddenLong = listOf("ip", "port", "protect-path", "no-udp", "daemon", "pidfile", "transparent")

  /** Returns null when acceptable, otherwise a short reason. */
  fun validate(args: String): String? {
    if (args.length > MAX_LENGTH) return "too long"
    if (!allowed.matches(args)) return "unsupported character"
    val tokens = args.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
    if (tokens.size > MAX_TOKENS) return "too many arguments"
    for (t in tokens) {
      if (t.startsWith("--")) {
        val name = t.removePrefix("--").substringBefore('=')
        // getopt_long accepts unambiguous prefixes, so block prefixes too.
        if (name.isEmpty() || forbiddenLong.any { it.startsWith(name) }) return "option $t is managed by Kervan"
      } else if (t.startsWith("-") && t.length > 1) {
        // Short options may be bundled (-NU); inspect the leading letter run.
        for (ch in t.substring(1)) {
          if (!ch.isLetter()) break
          if (ch in forbiddenShort) return "option -$ch is managed by Kervan"
        }
      }
    }
    return null
  }
}

/** One real HTTPS request and whether the engine was on for it. A fact about this network, now. */
data class AccessCheck(
  val host: String,
  val outcome: CheckOutcome,
  val engineOn: Boolean,
  val time: String,
  val status: Int? = null,
)
