package dev.kervan.dpi.settings

import android.content.Context
import android.content.SharedPreferences
import dev.kervan.dpi.engine.DnsProvider
import dev.kervan.dpi.engine.EngineSettings
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

/** Persists [EngineSettings] in private SharedPreferences. Process-wide singleton. */
class SettingsStore private constructor(private val prefs: SharedPreferences) {
  private val _settings = MutableStateFlow(load())
  val settings: StateFlow<EngineSettings> = _settings.asStateFlow()

  fun update(transform: (EngineSettings) -> EngineSettings) {
    _settings.update(transform)
    save(_settings.value)
  }

  private fun load(): EngineSettings {
    val d = EngineSettings()
    return EngineSettings(
      advanced = prefs.getBoolean(K_ADVANCED, d.advanced),
      disorder = prefs.getBoolean(K_DISORDER, d.disorder),
      splitAtSni = prefs.getBoolean(K_SPLIT, d.splitAtSni),
      tlsRecordAtSni = prefs.getBoolean(K_TLSREC, d.tlsRecordAtSni),
      oob = prefs.getBoolean(K_OOB, d.oob),
      customArgs = prefs.getString(K_CUSTOM, d.customArgs) ?: d.customArgs,
      dns = DnsProvider.fromKey(prefs.getString(K_DNS, d.dns.key)),
    )
  }

  private fun save(s: EngineSettings) {
    prefs.edit()
      .putBoolean(K_ADVANCED, s.advanced)
      .putBoolean(K_DISORDER, s.disorder)
      .putBoolean(K_SPLIT, s.splitAtSni)
      .putBoolean(K_TLSREC, s.tlsRecordAtSni)
      .putBoolean(K_OOB, s.oob)
      .putString(K_CUSTOM, s.customArgs)
      .putString(K_DNS, s.dns.key)
      .apply()
  }

  companion object {
    private const val K_ADVANCED = "advanced"
    private const val K_DISORDER = "disorder"
    private const val K_SPLIT = "split_sni"
    private const val K_TLSREC = "tlsrec_sni"
    private const val K_OOB = "oob"
    private const val K_CUSTOM = "custom_args"
    private const val K_DNS = "dns"

    @Volatile private var instance: SettingsStore? = null

    fun get(context: Context): SettingsStore = instance ?: synchronized(this) {
      instance ?: SettingsStore(
        context.applicationContext.getSharedPreferences("engine_settings", Context.MODE_PRIVATE),
      ).also { instance = it }
    }
  }
}
