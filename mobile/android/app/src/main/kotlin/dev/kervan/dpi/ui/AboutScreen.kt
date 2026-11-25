package dev.kervan.dpi.ui

import androidx.annotation.StringRes
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import dev.kervan.dpi.R
import dev.kervan.dpi.about.AppInfo
import dev.kervan.dpi.engine.EngineConfig
import dev.kervan.dpi.engine.EnginePhase
import dev.kervan.dpi.engine.EngineUiState
import dev.kervan.dpi.probe.AccessTarget

private val privacy = listOf(
  R.string.privacy_no_collection, R.string.privacy_traffic, R.string.privacy_dns,
  R.string.privacy_check, R.string.privacy_storage, R.string.privacy_local_proxy,
)

@Composable
fun AboutScreen(
  state: EngineUiState,
  selected: EngineConfig?,
  target: AccessTarget?,
  version: AppInfo.Version,
  onOpenUrl: (String) -> Unit,
  onShare: (String) -> Unit,
  onOpenAcknowledgements: () -> Unit,
  onBack: () -> Unit,
) {
  val diagnostics = diagnostics(state, selected, target, version)
  SubScreen(R.string.section_about, onBack) { padding ->
    LazyColumn(Modifier.fillMaxSize().testTag("about_list"), contentPadding = padding) {
      item {
        Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
          Image(painterResource(R.drawable.kervan_camel), contentDescription = null, modifier = Modifier.size(72.dp))
          Spacer(Modifier.height(Spacing.s))
          Text(
            stringResource(R.string.app_name),
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.semantics { heading() },
          )
          Text(
            stringResource(R.string.slogan),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
          )
        }
      }
      item {
        SectionHeader(stringResource(R.string.about_project))
        Group {
          LinkRow(
            stringResource(R.string.about_developer), AppInfo.DEVELOPER, "about_developer",
            stringResource(R.string.opens_browser),
          ) { onOpenUrl(AppInfo.DEVELOPER_URL) }
          RowDivider()
          LinkRow(
            stringResource(R.string.about_repository), AppInfo.REPOSITORY_URL.removePrefix("https://"),
            "about_repository", stringResource(R.string.opens_browser),
          ) { onOpenUrl(AppInfo.REPOSITORY_URL) }
        }
      }
      item {
        SectionHeader(stringResource(R.string.about_licenses))
        Group {
          LinkRow(
            stringResource(R.string.about_license), stringResource(R.string.about_license_sum), "about_license",
            stringResource(R.string.opens_browser),
          ) { onOpenUrl(AppInfo.LICENSE_URL) }
          RowDivider()
          LinkRow(
            stringResource(R.string.about_acknowledgements), stringResource(R.string.about_acknowledgements_sum),
            "about_acknowledgements", null, onOpenAcknowledgements,
          )
        }
      }
      item {
        SectionHeader(stringResource(R.string.about_privacy))
        Group {
          Column(Modifier.padding(Spacing.m).testTag("about_privacy")) {
            Text(stringResource(R.string.about_text), style = MaterialTheme.typography.bodyMedium)
            for (id in privacy) {
              Spacer(Modifier.height(Spacing.s))
              Text(stringResource(id), style = MaterialTheme.typography.bodyMedium)
            }
          }
        }
      }
      item {
        SectionHeader(stringResource(R.string.about_diagnostics))
        Group {
          Column(Modifier.padding(vertical = Spacing.s).testTag("about_diagnostics")) {
            for ((label, value) in diagnostics) {
              Column(Modifier.fillMaxWidth().padding(horizontal = Spacing.m, vertical = Spacing.s)) {
                Text(label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(value, style = MaterialTheme.typography.bodyLarge)
              }
            }
          }
        }
        OutlinedButton(
          onClick = { onShare(diagnostics.joinToString("\n") { (label, value) -> "$label: $value" }) },
          modifier = Modifier.fillMaxWidth().padding(top = Spacing.m).heightIn(min = 48.dp).testTag("share_diagnostics"),
        ) { Text(stringResource(R.string.action_share)) }
      }
    }
  }
}

/** Shown and shared; a custom target appears by host only. */
@Composable
private fun diagnostics(
  state: EngineUiState,
  selected: EngineConfig?,
  target: AccessTarget?,
  version: AppInfo.Version,
): List<Pair<String, String>> {
  // While running, report what the engine really uses, not a pending selection.
  val config = state.activeConfig ?: selected
  val none = stringResource(R.string.value_none)
  val check = state.accessCheck
  return listOf(
    stringResource(R.string.diag_version) to version.name,
    stringResource(R.string.diag_code) to version.code.toString(),
    stringResource(R.string.diag_platform) to AppInfo.platform(),
    stringResource(R.string.diag_status) to stringResource(statusLabel(state.phase)),
    stringResource(R.string.diag_args) to (config?.desyncArgs?.ifEmpty { stringResource(R.string.value_relay_only) } ?: none),
    stringResource(R.string.row_dns) to (config?.let { "${it.dns.label} (${it.dns.v4}, ${it.dns.v6})" } ?: none),
    stringResource(R.string.diag_target) to (target?.host ?: stringResource(R.string.target_invalid)),
    stringResource(R.string.diag_last_check) to
      (check?.let { "${accessCheckText(it)} · ${accessCheckEngine(it)}" } ?: none),
  )
}

@Composable
fun AcknowledgementsScreen(text: String, onBack: () -> Unit) {
  // One item per paragraph: the license texts are long.
  val paragraphs = remember(text) { text.split(Regex("\n\\s*\n")).filter { it.isNotBlank() } }
  SubScreen(R.string.about_acknowledgements, onBack) { padding ->
    SelectionContainer {
      LazyColumn(Modifier.fillMaxSize().testTag("acknowledgements_list"), contentPadding = padding) {
        items(paragraphs) {
          Text(it, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(bottom = Spacing.s))
        }
      }
    }
  }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SubScreen(@StringRes title: Int, onBack: () -> Unit, content: @Composable (PaddingValues) -> Unit) {
  Scaffold(
    containerColor = MaterialTheme.colorScheme.surface,
    topBar = {
      TopAppBar(
        title = { Text(stringResource(title)) },
        navigationIcon = {
          IconButton(onClick = onBack, modifier = Modifier.testTag("nav_back")) {
            Icon(painterResource(R.drawable.ic_arrow_back), contentDescription = stringResource(R.string.nav_back))
          }
        },
        colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface),
      )
    },
  ) { inner ->
    content(
      PaddingValues(
        start = Spacing.m, end = Spacing.m,
        top = inner.calculateTopPadding() + Spacing.s, bottom = inner.calculateBottomPadding() + Spacing.l,
      ),
    )
  }
}

@Composable
fun LinkRow(title: String, summary: String, tag: String, clickLabel: String?, onClick: () -> Unit) {
  Column(
    Modifier
      .fillMaxWidth()
      .heightIn(min = 56.dp)
      .clickable(role = Role.Button, onClickLabel = clickLabel, onClick = onClick)
      .padding(horizontal = Spacing.m, vertical = Spacing.s)
      .testTag(tag),
  ) {
    Text(title, style = MaterialTheme.typography.bodyLarge)
    Text(summary, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
  }
}

@StringRes
fun statusLabel(phase: EnginePhase): Int = when (phase) {
  EnginePhase.STOPPED -> R.string.status_stopped
  EnginePhase.STARTING -> R.string.status_starting
  EnginePhase.RUNNING -> R.string.status_running
  EnginePhase.STOPPING -> R.string.status_stopping
  EnginePhase.FAILED -> R.string.status_failed
}
