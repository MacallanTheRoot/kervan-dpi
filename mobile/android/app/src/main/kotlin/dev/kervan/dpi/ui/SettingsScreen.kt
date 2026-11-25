package dev.kervan.dpi.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.kervan.dpi.R
import dev.kervan.dpi.engine.DnsProvider
import dev.kervan.dpi.engine.EngineSettings

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
  settings: EngineSettings,
  engineActive: Boolean,
  log: List<String>,
  versionName: String,
  check: CheckUi,
  onOpenAbout: () -> Unit,
  onUpdate: ((EngineSettings) -> EngineSettings) -> Unit,
  onBack: () -> Unit,
) {
  Scaffold(
    containerColor = MaterialTheme.colorScheme.surface,
    topBar = {
      TopAppBar(
        title = { Text(stringResource(R.string.settings_title)) },
        navigationIcon = {
          IconButton(onClick = onBack, modifier = Modifier.testTag("nav_back")) {
            Icon(painterResource(R.drawable.ic_arrow_back), contentDescription = stringResource(R.string.nav_back))
          }
        },
        colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface),
      )
    },
  ) { inner ->
    LazyColumn(
      Modifier.fillMaxSize().testTag("settings_list"),
      contentPadding = PaddingValues(
        start = Spacing.m, end = Spacing.m,
        top = inner.calculateTopPadding() + Spacing.s, bottom = inner.calculateBottomPadding() + Spacing.l,
      ),
    ) {
      if (engineActive) {
        item { Note(stringResource(R.string.applies_on_reconnect)) }
      }
      item {
        SectionHeader(stringResource(R.string.section_engine))
        Group {
          SwitchRow(
            title = stringResource(R.string.advanced_title),
            summary = stringResource(R.string.advanced_summary),
            checked = settings.advanced,
            tag = "advanced_switch",
            onChange = { on -> onUpdate { it.copy(advanced = on) } },
          )
        }
      }
      item {
        AnimatedVisibility(visible = settings.advanced) {
          AdvancedSections(settings, onUpdate)
        }
      }
      item { ConnectionCheckSection(check) }
      item {
        SectionHeader(stringResource(R.string.section_activity))
        Group {
          val lines = log.takeLast(40)
          Column(Modifier.padding(Spacing.m)) {
            if (lines.isEmpty()) {
              Text(
                stringResource(R.string.activity_empty),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
              )
            }
            for (line in lines) {
              Text(
                line,
                fontFamily = FontFamily.Monospace,
                fontSize = 12.sp,
                lineHeight = 18.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
              )
            }
          }
        }
      }
      item {
        SectionHeader(stringResource(R.string.section_about))
        Group {
          LinkRow(
            stringResource(R.string.about_open), stringResource(R.string.version, versionName), "open_about", null,
            onOpenAbout,
          )
        }
      }
    }
  }
}

@Composable
private fun AdvancedSections(settings: EngineSettings, onUpdate: ((EngineSettings) -> EngineSettings) -> Unit) {
  val customInUse = settings.customArgs.isNotBlank()
  Column {
    SectionHeader(stringResource(R.string.section_methods))
    Group {
      SwitchRow(
        stringResource(R.string.method_disorder), stringResource(R.string.method_disorder_sum),
        settings.disorder, "method_disorder", enabled = !customInUse,
      ) { v -> onUpdate { it.copy(disorder = v) } }
      RowDivider()
      SwitchRow(
        stringResource(R.string.method_split), stringResource(R.string.method_split_sum),
        settings.splitAtSni, "method_split", enabled = !customInUse,
      ) { v -> onUpdate { it.copy(splitAtSni = v) } }
      RowDivider()
      SwitchRow(
        stringResource(R.string.method_tlsrec), stringResource(R.string.method_tlsrec_sum),
        settings.tlsRecordAtSni, "method_tlsrec", enabled = !customInUse,
      ) { v -> onUpdate { it.copy(tlsRecordAtSni = v) } }
      RowDivider()
      SwitchRow(
        stringResource(R.string.method_oob), stringResource(R.string.method_oob_sum),
        settings.oob, "method_oob", enabled = !customInUse,
      ) { v -> onUpdate { it.copy(oob = v) } }
    }
    if (settings.relayOnly) {
      Note(stringResource(R.string.relay_only_warning))
    }

    SectionHeader(stringResource(R.string.section_custom))
    val error = settings.error()
    OutlinedTextField(
      value = settings.customArgs,
      onValueChange = { v -> onUpdate { it.copy(customArgs = v) } },
      singleLine = true,
      isError = error != null,
      supportingText = {
        Text(if (error != null) stringResource(R.string.custom_error, error) else stringResource(R.string.custom_hint))
      },
      textStyle = MaterialTheme.typography.bodyLarge.copy(fontFamily = FontFamily.Monospace),
      modifier = Modifier.fillMaxWidth().testTag("custom_args"),
    )

    SectionHeader(stringResource(R.string.section_dns))
    Group {
      Column {
        Text(
          stringResource(R.string.dns_summary),
          style = MaterialTheme.typography.bodyMedium,
          color = MaterialTheme.colorScheme.onSurfaceVariant,
          modifier = Modifier.padding(start = Spacing.m, end = Spacing.m, top = Spacing.m, bottom = Spacing.xs),
        )
        for (p in DnsProvider.entries) {
          RadioRow(
            title = p.label,
            summary = "${p.v4} · ${p.v6}",
            selected = settings.dns == p,
            tag = "dns_${p.key}",
          ) { onUpdate { it.copy(dns = p) } }
        }
      }
    }

    Spacer(Modifier.padding(top = Spacing.l))
    OutlinedButton(
      onClick = { onUpdate { it.reset() } },
      modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp).testTag("reset_defaults"),
    ) { Text(stringResource(R.string.action_reset)) }
  }
}

@Composable
internal fun SectionHeader(text: String) {
  Text(
    text,
    style = MaterialTheme.typography.titleSmall,
    color = MaterialTheme.colorScheme.primary,
    modifier = Modifier.padding(start = Spacing.m, top = Spacing.l, bottom = Spacing.s).semantics { heading() },
  )
}

@Composable
internal fun Group(content: @Composable () -> Unit) {
  Surface(
    color = MaterialTheme.colorScheme.surfaceContainerLow,
    shape = RoundedCornerShape(16.dp),
    modifier = Modifier.fillMaxWidth(),
  ) { Column { content() } }
}

@Composable
internal fun RowDivider() = HorizontalDivider(
  modifier = Modifier.padding(horizontal = Spacing.m),
  color = MaterialTheme.colorScheme.outlineVariant,
)

@Composable
internal fun Note(text: String) {
  Text(
    text,
    style = MaterialTheme.typography.bodyMedium,
    color = MaterialTheme.colorScheme.onSurfaceVariant,
    modifier = Modifier.padding(start = Spacing.m, end = Spacing.m, top = Spacing.m),
  )
}

@Composable
private fun SwitchRow(
  title: String,
  summary: String,
  checked: Boolean,
  tag: String,
  enabled: Boolean = true,
  onChange: (Boolean) -> Unit,
) {
  Row(
    Modifier
      .fillMaxWidth()
      .heightIn(min = 64.dp)
      .toggleable(value = checked, enabled = enabled, role = Role.Switch, onValueChange = onChange)
      .padding(horizontal = Spacing.m, vertical = Spacing.m - Spacing.xs)
      .testTag(tag),
    verticalAlignment = Alignment.CenterVertically,
  ) {
    Column(Modifier.weight(1f)) {
      Text(
        title,
        style = MaterialTheme.typography.bodyLarge,
        color = if (enabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
      )
      Text(summary, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
    Spacer(Modifier.width(Spacing.m))
    Switch(checked = checked, onCheckedChange = null, enabled = enabled)
  }
}

@Composable
internal fun RadioRow(title: String, summary: String, selected: Boolean, tag: String, onSelect: () -> Unit) {
  Row(
    Modifier
      .fillMaxWidth()
      .heightIn(min = 56.dp)
      .selectable(selected = selected, role = Role.RadioButton, onClick = onSelect)
      .padding(horizontal = Spacing.m, vertical = Spacing.s)
      .testTag(tag),
    verticalAlignment = Alignment.CenterVertically,
  ) {
    RadioButton(selected = selected, onClick = null)
    Spacer(Modifier.width(Spacing.m))
    Column {
      Text(title, style = MaterialTheme.typography.bodyLarge)
      Text(summary, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
  }
}
