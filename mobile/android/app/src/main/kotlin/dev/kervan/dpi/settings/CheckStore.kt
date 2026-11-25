package dev.kervan.dpi.settings

import android.content.Context
import android.content.SharedPreferences
import dev.kervan.dpi.probe.CheckSettings
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Persists [CheckSettings], apart from the engine's settings. Process-wide singleton. */
class CheckStore private constructor(private val prefs: SharedPreferences) {
  private val _settings = MutableStateFlow(
    CheckSettings.restore(prefs.getString(K_TARGET, null), prefs.getString(K_CUSTOM, null)),
  )
  val settings: StateFlow<CheckSettings> = _settings.asStateFlow()

  fun update(value: CheckSettings) {
    _settings.value = value
    prefs.edit().putString(K_TARGET, value.key).putString(K_CUSTOM, value.customText).apply()
  }

  companion object {
    private const val K_TARGET = "target"
    private const val K_CUSTOM = "custom_url"

    @Volatile private var instance: CheckStore? = null

    fun get(context: Context): CheckStore = instance ?: synchronized(this) {
      instance ?: CheckStore(
        context.applicationContext.getSharedPreferences("access_check", Context.MODE_PRIVATE),
      ).also { instance = it }
    }
  }
}
