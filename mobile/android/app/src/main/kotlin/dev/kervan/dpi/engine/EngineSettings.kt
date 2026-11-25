package dev.kervan.dpi.engine

/** Resolvers announced on the VPN interface; queries travel as UDP through the engine. */
enum class DnsProvider(val key: String, val label: String, val v4: String, val v6: String) {
  CLOUDFLARE("cloudflare", "Cloudflare", "1.1.1.1", "2606:4700:4700::1111"),
  GOOGLE("google", "Google", "8.8.8.8", "2001:4860:4860::8888"),
  QUAD9("quad9", "Quad9", "9.9.9.9", "2620:fe::fe");

  companion object {
    fun fromKey(key: String?): DnsProvider = entries.firstOrNull { it.key == key } ?: CLOUDFLARE
  }
}

/** What the engine is actually started with. */
data class EngineConfig(val desyncArgs: String, val dns: DnsProvider)

/**
 * User settings. Only options backed by the engine are modelled: ByeDPI desync
 * methods (-d, -s, -r, -o), raw ByeDPI arguments, and the DNS resolver the VPN
 * interface announces. With advanced mode off the verified defaults always apply.
 */
data class EngineSettings(
  val advanced: Boolean = false,
  val disorder: Boolean = true,        // -d1
  val splitAtSni: Boolean = true,      // -s1+s
  val tlsRecordAtSni: Boolean = true,  // -r1+s
  val oob: Boolean = false,            // -o1
  val customArgs: String = "",
  val dns: DnsProvider = DnsProvider.CLOUDFLARE,
) {
  private val custom get() = customArgs.trim()

  /** A reason the settings cannot be applied, or null. */
  fun error(): String? = if (advanced && custom.isNotEmpty()) DesyncArgs.validate(custom) else null

  /** Advanced mode with no method selected: traffic is relayed but not modified. */
  val relayOnly get() = advanced && custom.isEmpty() && !disorder && !splitAtSni && !tlsRecordAtSni && !oob

  fun toConfigOrNull(): EngineConfig? = if (error() == null) toConfig() else null

  fun toConfig(): EngineConfig {
    if (!advanced) return EngineConfig(DesyncArgs.DEFAULT, DnsProvider.CLOUDFLARE)
    check(error() == null) { "invalid settings" }
    val args = custom.ifEmpty {
      buildList {
        if (disorder) add("-d1")
        if (splitAtSni) add("-s1+s")
        if (tlsRecordAtSni) add("-r1+s")
        if (oob) add("-o1")
      }.joinToString(" ")
    }
    return EngineConfig(args, dns)
  }

  fun reset() = EngineSettings()
}
