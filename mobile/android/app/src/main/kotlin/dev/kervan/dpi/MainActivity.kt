package dev.kervan.dpi

import android.Manifest
import android.content.pm.PackageManager
import android.net.VpnService
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.lifecycleScope
import dev.kervan.dpi.about.AppInfo
import dev.kervan.dpi.engine.AccessCheck
import dev.kervan.dpi.engine.EngineConfig
import dev.kervan.dpi.engine.EnginePhase
import dev.kervan.dpi.probe.ConnectivityProbe
import dev.kervan.dpi.settings.CheckStore
import dev.kervan.dpi.settings.SettingsStore
import dev.kervan.dpi.ui.AboutScreen
import dev.kervan.dpi.ui.AcknowledgementsScreen
import dev.kervan.dpi.ui.CheckUi
import dev.kervan.dpi.ui.KervanTheme
import dev.kervan.dpi.ui.MainScreen
import dev.kervan.dpi.ui.SettingsScreen
import dev.kervan.dpi.vpn.EngineStatus
import dev.kervan.dpi.vpn.KervanVpnService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

  private enum class Screen { HOME, SETTINGS, ABOUT, ACKNOWLEDGEMENTS }

  private var pendingConfig: EngineConfig? = null
  private var checking by mutableStateOf(false)

  private val vpnConsent = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
    val config = pendingConfig
    pendingConfig = null
    if (result.resultCode == RESULT_OK && config != null) {
      KervanVpnService.start(this, config)
    } else {
      EngineStatus.log("VPN permission was not granted.")
    }
  }

  private val notifPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    enableEdgeToEdge()
    val store = SettingsStore.get(this)
    val checkStore = CheckStore.get(this)
    setContent {
      val state by EngineStatus.state.collectAsStateWithLifecycle()
      val settings by store.settings.collectAsStateWithLifecycle()
      val checkSettings by checkStore.settings.collectAsStateWithLifecycle()
      var screen by rememberSaveable { mutableStateOf(Screen.HOME) }
      val version = remember { AppInfo.version(this) }
      val selected = settings.toConfigOrNull()
      val back = {
        screen = when (screen) {
          Screen.ACKNOWLEDGEMENTS -> Screen.ABOUT
          Screen.ABOUT -> Screen.SETTINGS
          else -> Screen.HOME
        }
      }
      BackHandler(enabled = screen != Screen.HOME, onBack = back)
      KervanTheme {
        AnimatedContent(targetState = screen, label = "destination") { shown ->
          when (shown) {
            Screen.HOME -> MainScreen(
              state = state,
              selected = selected,
              checking = checking,
              targetValid = checkSettings.target != null,
              onToggle = {
                if (state.canDisable) KervanVpnService.stop(this@MainActivity) else selected?.let(::enable)
              },
              onReconnect = { selected?.let { KervanVpnService.start(this@MainActivity, it) } },
              onCheck = ::checkAccess,
              onOpenSettings = { screen = Screen.SETTINGS },
            )
            Screen.SETTINGS -> SettingsScreen(
              settings = settings,
              engineActive = state.phase == EnginePhase.RUNNING,
              log = state.log,
              versionName = version.name,
              check = CheckUi(
                settings = checkSettings,
                result = state.accessCheck,
                checking = checking,
                engineSettled = state.settled,
                onChange = { value ->
                  if (value != checkSettings) {
                    checkStore.update(value)
                    EngineStatus.clearCheck()
                  }
                },
                onCheck = ::checkAccess,
              ),
              onOpenAbout = { screen = Screen.ABOUT },
              onUpdate = store::update,
              onBack = back,
            )
            Screen.ABOUT -> AboutScreen(
              state = state,
              selected = selected,
              target = checkSettings.target,
              version = version,
              onOpenUrl = { AppInfo.openInBrowser(this@MainActivity, it) },
              onShare = { AppInfo.share(this@MainActivity, it) },
              onOpenAcknowledgements = { screen = Screen.ACKNOWLEDGEMENTS },
              onBack = back,
            )
            Screen.ACKNOWLEDGEMENTS -> AcknowledgementsScreen(
              text = remember { AppInfo.acknowledgements(this@MainActivity) },
              onBack = back,
            )
          }
        }
      }
    }
  }

  /** One real HTTPS request to the selected target, through the tunnel when it runs; shown as-is. */
  private fun checkAccess() {
    val before = EngineStatus.state.value
    val target = CheckStore.get(this).settings.value.target ?: return
    if (checking || !before.settled) return
    checking = true
    lifecycleScope.launch(Dispatchers.IO) {
      try {
        val engineOn = before.phase == EnginePhase.RUNNING
        EngineStatus.log("Access check (engine ${before.phase.name.lowercase()})")
        val r = ConnectivityProbe.probe(target)
        EngineStatus.log(ConnectivityProbe.format(r))
        EngineStatus.accessCheck(
          AccessCheck(target.host, r.outcome, engineOn, EngineStatus.now().substring(0, 5), r.status),
          before.checkEpoch,
        )
      } finally {
        checking = false
      }
    }
  }

  private fun enable(config: EngineConfig) {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
      checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
    ) {
      notifPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
    }
    // The user must explicitly approve the system VPN dialog the first time.
    val consent = VpnService.prepare(this)
    if (consent != null) {
      pendingConfig = config
      vpnConsent.launch(consent)
    } else {
      KervanVpnService.start(this, config)
    }
  }
}
