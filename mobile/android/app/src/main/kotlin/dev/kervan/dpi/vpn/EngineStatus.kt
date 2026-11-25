package dev.kervan.dpi.vpn

import android.util.Log
import dev.kervan.dpi.engine.AccessCheck
import dev.kervan.dpi.engine.EngineConfig
import dev.kervan.dpi.engine.EnginePhase
import dev.kervan.dpi.engine.EngineUiState
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

/** Process-wide state shared by the service (writer) and the UI (reader). */
object EngineStatus {
  private val _state = MutableStateFlow(EngineUiState())
  val state: StateFlow<EngineUiState> = _state.asStateFlow()
  private val clock = SimpleDateFormat("HH:mm:ss", Locale.ROOT)

  fun now(): String = clock.format(Date())

  /** Any phase change ends the previous session's config and access check. */
  fun phase(phase: EnginePhase, error: String? = null, activeConfig: EngineConfig? = null) {
    Log.i("KervanStatus", "phase=$phase error=$error")
    _state.update { it.withoutCheck().copy(phase = phase, error = error, activeConfig = activeConfig) }
  }

  fun accessCheck(check: AccessCheck, epoch: Int) = _state.update { it.withCheck(check, epoch) }

  fun clearCheck() = _state.update { it.withoutCheck() }

  fun log(message: String) {
    val line = "${now()}  $message"
    Log.i("KervanStatus", message)
    _state.update { it.withLog(line) }
  }
}
