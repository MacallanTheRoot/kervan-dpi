package dev.kervan.dpi.ui

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performScrollToNode
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.performTextReplacement
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import dev.kervan.dpi.R
import dev.kervan.dpi.engine.AccessCheck
import dev.kervan.dpi.engine.DnsProvider
import dev.kervan.dpi.engine.EngineConfig
import dev.kervan.dpi.engine.EnginePhase
import dev.kervan.dpi.engine.EngineSettings
import dev.kervan.dpi.engine.EngineUiState
import dev.kervan.dpi.about.AppInfo
import dev.kervan.dpi.probe.AccessTarget
import dev.kervan.dpi.probe.CheckOutcome
import dev.kervan.dpi.probe.CheckSettings
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ScreensTest {
  @get:Rule val rule = createComposeRule()
  private val ctx = InstrumentationRegistry.getInstrumentation().targetContext
  private fun str(id: Int, vararg a: Any) = ctx.getString(id, *a)

  private fun main(state: EngineUiState, selected: EngineConfig? = EngineSettings().toConfig(), onToggle: () -> Unit = {}) =
    rule.setContent {
      KervanTheme {
        MainScreen(state, selected, checking = false, targetValid = true, onToggle = onToggle, onReconnect = {}, onCheck = {}, onOpenSettings = {})
      }
    }

  private fun checkUi(
    settings: CheckSettings = CheckSettings(),
    result: AccessCheck? = null,
    onChange: (CheckSettings) -> Unit = {},
    onCheck: () -> Unit = {},
  ) = CheckUi(settings, result, checking = false, engineSettled = true, onChange = onChange, onCheck = onCheck)

  @Test
  fun stoppedShowsOneEnableActionAndNoEngineParameters() {
    var toggles = 0
    main(EngineUiState(phase = EnginePhase.STOPPED), onToggle = { toggles++ })
    rule.onNodeWithTag("primary_action").assertIsEnabled()
    rule.onNodeWithText(str(R.string.action_enable)).assertIsDisplayed().performClick()
    assertEquals(1, toggles)
    rule.onNodeWithTag("open_settings").assertIsDisplayed()
    rule.onNodeWithTag("custom_args").assertDoesNotExist()
    rule.onNodeWithTag("access_check").assertDoesNotExist()
  }

  @Test
  fun invalidSettingsDisableEnable() {
    main(EngineUiState(phase = EnginePhase.STOPPED), selected = null)
    rule.onNodeWithTag("primary_action").assertIsNotEnabled()
  }

  @Test
  fun runningSeparatesEngineStateFromAccess() {
    val cfg = EngineSettings().toConfig()
    main(EngineUiState(phase = EnginePhase.RUNNING, activeConfig = cfg))
    rule.onNodeWithText(str(R.string.action_disable)).assertIsDisplayed()
    rule.onNodeWithText(str(R.string.access_unchecked)).assertIsDisplayed()
    rule.onNodeWithText(str(R.string.value_recommended)).assertIsDisplayed()
    rule.onNodeWithTag("reconnect_notice").assertDoesNotExist()
  }

  @Test
  fun accessResultIsShownAsReported() {
    val cfg = EngineSettings().toConfig()
    main(EngineUiState(EnginePhase.RUNNING, activeConfig = cfg, accessCheck = AccessCheck("example.org", CheckOutcome.NO_ANSWER, true, "12:00")))
    rule.onNodeWithText(str(R.string.access_fail, "example.org", "12:00")).assertIsDisplayed()
  }

  @Test
  fun changedSettingsAskForReconnect() {
    val running = EngineConfig("-d1", DnsProvider.CLOUDFLARE)
    main(EngineUiState(phase = EnginePhase.RUNNING, activeConfig = running), selected = EngineSettings().toConfig())
    rule.onNodeWithTag("reconnect_notice").assertIsDisplayed()
  }

  @Test
  fun advancedModeIsOffByDefaultAndRevealsOnlySupportedControls() {
    var settings by mutableStateOf(EngineSettings())
    rule.setContent {
      KervanTheme {
        SettingsScreen(settings, false, emptyList(), "test", checkUi(), onOpenAbout = {}, onUpdate = { settings = it(settings) }, onBack = {})
      }
    }
    rule.onNodeWithTag("advanced_switch").assertIsOff()
    rule.onNodeWithTag("method_disorder").assertDoesNotExist()
    rule.onNodeWithTag("advanced_switch").performClick()
    assertTrue(settings.advanced)
    rule.onNodeWithTag("settings_list").performScrollToNode(hasTestTag("method_oob"))
    rule.onNodeWithTag("method_oob").performClick()
    assertTrue(settings.oob)
    rule.onNodeWithTag("settings_list").performScrollToNode(hasTestTag("custom_args"))
    rule.onNodeWithTag("custom_args").performTextReplacement("-i 0.0.0.0")
    assertEquals(null, settings.toConfigOrNull())
    rule.onNodeWithTag("settings_list").performScrollToNode(hasTestTag("reset_defaults"))
    rule.onNodeWithTag("reset_defaults").performClick()
    assertEquals(EngineSettings(), settings)
  }

  @Test
  fun connectionCheckSelectsTargetsAndRejectsUnsafeAddresses() {
    var check by mutableStateOf(CheckSettings())
    var runs = 0
    rule.setContent {
      KervanTheme {
        SettingsScreen(
          EngineSettings(), false, emptyList(), "test",
          checkUi(check, onChange = { check = it }, onCheck = { runs++ }),
          onOpenAbout = {}, onUpdate = {}, onBack = {},
        )
      }
    }
    val list = rule.onNodeWithTag("settings_list")
    list.performScrollToNode(hasTestTag("target_google"))
    rule.onNodeWithTag("target_google").performClick()
    assertEquals(AccessTarget.GOOGLE, check.target)
    rule.onNodeWithTag("target_custom").performScrollTo().performClick()
    rule.onNodeWithTag("custom_target").performScrollTo().performTextReplacement("http://example.org")
    rule.onNodeWithText(str(R.string.target_custom_error)).assertExists()
    rule.onNodeWithTag("check_now").performScrollTo().assertIsNotEnabled()
    rule.onNodeWithTag("custom_target").performScrollTo().performTextReplacement("https://example.org")
    rule.onNodeWithTag("check_now").performScrollTo().assertIsEnabled().performClick()
    assertEquals(1, runs)
  }

  @Test
  fun resultSaysWhetherKervanWasOn() {
    val result = AccessCheck("example.org", CheckOutcome.ANSWERED, engineOn = false, time = "12:00")
    rule.setContent {
      KervanTheme {
        SettingsScreen(
          EngineSettings(), false, emptyList(), "test", checkUi(result = result),
          onOpenAbout = {}, onUpdate = {}, onBack = {},
        )
      }
    }
    rule.onNodeWithTag("settings_list").performScrollToNode(hasText(str(R.string.check_engine_off), substring = true))
    rule.onNodeWithText(str(R.string.access_answered, "example.org", "12:00"), substring = true).assertExists()
  }

  @Test
  fun aboutShowsIdentityAndInstalledVersionAndOpensLinks() {
    val version = AppInfo.version(ctx)
    val opened = mutableListOf<String>()
    var shared = ""
    val custom = AccessTarget.custom("https://example.org/private?token=abc")
    rule.setContent {
      KervanTheme {
        AboutScreen(
          EngineUiState(), EngineSettings().toConfig(), custom, version,
          onOpenUrl = { opened += it }, onShare = { shared = it }, onOpenAcknowledgements = {}, onBack = {},
        )
      }
    }
    rule.onNodeWithText("Kervan DPI").assertIsDisplayed()
    rule.onNodeWithText("Yol Açık, Kervan Yürür.").assertIsDisplayed()
    rule.onNodeWithTag("about_developer").assertTextContains("MacallanTheRoot")
    val list = rule.onNodeWithTag("about_list")
    for (tag in listOf("about_developer", "about_repository", "about_license")) {
      list.performScrollToNode(hasTestTag(tag))
      rule.onNodeWithTag(tag).performClick()
    }
    assertEquals(
      listOf("https://github.com/macallanTheRoot", "https://github.com/MacallanTheRoot/kervan-dpi", AppInfo.LICENSE_URL),
      opened,
    )
    list.performScrollToNode(hasTestTag("share_diagnostics"))
    rule.onNodeWithTag("share_diagnostics").performClick()
    val installed = ctx.packageManager.getPackageInfo(ctx.packageName, 0)
    assertTrue(shared, installed.versionName!! in shared)
    assertTrue(shared, "${str(R.string.diag_code)}: ${installed.longVersionCode}" in shared)
    assertTrue(shared, "example.org" in shared)
    assertTrue("custom path leaked: $shared", "private" !in shared && "token" !in shared)
  }

  @Test
  fun acknowledgementsAreShipped() {
    val text = AppInfo.acknowledgements(ctx)
    for (part in listOf("hufrea", "hev-socks5-tunnel", "Swedish Institute of Computer Science", "Apache License")) {
      assertTrue(part, part in text)
    }
    rule.setContent { KervanTheme { AcknowledgementsScreen(text, onBack = {}) } }
    rule.onNodeWithTag("acknowledgements_list").assertIsDisplayed()
  }
}
