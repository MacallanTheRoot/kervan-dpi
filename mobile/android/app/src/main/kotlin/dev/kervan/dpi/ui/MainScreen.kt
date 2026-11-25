package dev.kervan.dpi.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import dev.kervan.dpi.R
import dev.kervan.dpi.engine.AccessCheck
import dev.kervan.dpi.engine.DesyncArgs
import dev.kervan.dpi.engine.EngineConfig
import dev.kervan.dpi.engine.EnginePhase
import dev.kervan.dpi.engine.EngineUiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
  state: EngineUiState,
  selected: EngineConfig?,
  checking: Boolean,
  targetValid: Boolean,
  onToggle: () -> Unit,
  onReconnect: () -> Unit,
  onCheck: () -> Unit,
  onOpenSettings: () -> Unit,
) {
  Scaffold(
    containerColor = MaterialTheme.colorScheme.surface,
    topBar = {
      TopAppBar(
        title = { Text(stringResource(R.string.app_name)) },
        actions = {
          IconButton(onClick = onOpenSettings, modifier = Modifier.testTag("open_settings")) {
            Icon(painterResource(R.drawable.ic_settings), contentDescription = stringResource(R.string.nav_settings))
          }
        },
        colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface),
      )
    },
  ) { inner ->
    Column(Modifier.fillMaxSize().padding(inner).padding(horizontal = Spacing.m)) {
      // Content sits centred in the space above the action; it scrolls when it does not fit.
      Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.CenterStart) {
      Column(
        Modifier.verticalScroll(rememberScrollState()).padding(top = Spacing.l),
      ) {
        CamelMark(walking = state.phase == EnginePhase.RUNNING)
        Spacer(Modifier.height(Spacing.l))
        StatusBlock(state)
        if (state.needsReconnect(selected)) {
          Spacer(Modifier.height(Spacing.m))
          ReconnectNotice(onReconnect)
        }
        if (state.phase == EnginePhase.RUNNING && state.activeConfig != null) {
          Spacer(Modifier.height(Spacing.l))
          SessionDetails(state.activeConfig, state.accessCheck, checking, targetValid, onCheck)
        }
        Spacer(Modifier.height(Spacing.l))
      }
      }
      PrimaryAction(state, enabled = selected != null || state.canDisable, onToggle)
      Text(
        stringResource(R.string.slogan),
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(vertical = Spacing.m),
      )
    }
  }
}

/** The brand mark carries the state: grey when idle, blue when the caravan walks. */
@Composable
private fun CamelMark(walking: Boolean) {
  Image(
    painter = painterResource(R.drawable.kervan_camel),
    contentDescription = null,
    colorFilter = if (walking) null else ColorFilter.colorMatrix(ColorMatrix().apply { setToSaturation(0f) }),
    modifier = Modifier.size(88.dp),
  )
}

@Composable
private fun StatusBlock(state: EngineUiState) {
  val status = KervanTheme.status
  val (label, headline) = when (state.phase) {
    EnginePhase.STOPPED -> R.string.status_stopped to R.string.headline_stopped
    EnginePhase.STARTING -> R.string.status_starting to R.string.headline_starting
    EnginePhase.RUNNING -> R.string.status_running to R.string.headline_running
    EnginePhase.STOPPING -> R.string.status_stopping to R.string.headline_stopping
    EnginePhase.FAILED -> R.string.status_failed to R.string.headline_failed
  }
  val dot = when (state.phase) {
    EnginePhase.RUNNING -> status.active
    EnginePhase.FAILED -> MaterialTheme.colorScheme.error
    else -> status.inactive
  }
  Column(Modifier.semantics(mergeDescendants = true) { liveRegion = LiveRegionMode.Polite }) {
    Row(verticalAlignment = Alignment.CenterVertically) {
      Box(Modifier.size(8.dp).background(dot, CircleShape))
      Spacer(Modifier.width(Spacing.s))
      Text(
        stringResource(label),
        style = MaterialTheme.typography.labelLarge,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.testTag("status_label"),
      )
    }
    Spacer(Modifier.height(Spacing.s))
    Text(
      stringResource(headline),
      style = MaterialTheme.typography.headlineMedium,
      color = MaterialTheme.colorScheme.onSurface,
      modifier = Modifier.semantics { heading() },
    )
    val detail = when {
      state.error != null -> state.error
      state.phase == EnginePhase.RUNNING && state.accessCheck == null -> stringResource(R.string.detail_running)
      state.phase == EnginePhase.RUNNING -> stringResource(R.string.detail_running_checked)
      state.phase == EnginePhase.STOPPED -> stringResource(R.string.detail_stopped)
      else -> null
    }
    if (detail != null) {
      Spacer(Modifier.height(Spacing.s))
      Text(
        detail,
        style = MaterialTheme.typography.bodyLarge,
        color = if (state.error != null) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant,
      )
    }
  }
}

@Composable
private fun ReconnectNotice(onReconnect: () -> Unit) {
  Surface(
    color = MaterialTheme.colorScheme.secondaryContainer,
    shape = RoundedCornerShape(12.dp),
    modifier = Modifier.fillMaxWidth().testTag("reconnect_notice"),
  ) {
    Row(
      Modifier.padding(start = Spacing.m, end = Spacing.s, top = Spacing.s, bottom = Spacing.s),
      verticalAlignment = Alignment.CenterVertically,
    ) {
      Text(
        stringResource(R.string.reconnect_needed),
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSecondaryContainer,
        modifier = Modifier.weight(1f),
      )
      TextButton(onClick = onReconnect) { Text(stringResource(R.string.action_reconnect)) }
    }
  }
}

@Composable
private fun SessionDetails(
  config: EngineConfig,
  check: AccessCheck?,
  checking: Boolean,
  targetValid: Boolean,
  onCheck: () -> Unit,
) {
  val method = stringResource(
    when (config.desyncArgs) {
      DesyncArgs.DEFAULT -> R.string.value_recommended
      "" -> R.string.value_relay_only
      else -> R.string.value_custom
    },
  )
  Surface(
    color = MaterialTheme.colorScheme.surfaceContainerLow,
    shape = RoundedCornerShape(16.dp),
    modifier = Modifier.fillMaxWidth(),
  ) {
    Column(Modifier.padding(vertical = Spacing.s)) {
      DetailRow(stringResource(R.string.row_method), method)
      DetailRow(stringResource(R.string.row_dns), config.dns.label)
      AccessRow(check, checking, targetValid, onCheck)
    }
  }
}

@Composable
private fun DetailRow(label: String, value: String) {
  Row(
    Modifier.fillMaxWidth().heightIn(min = 48.dp).padding(horizontal = Spacing.m),
    verticalAlignment = Alignment.CenterVertically,
  ) {
    Text(label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    Spacer(Modifier.weight(1f))
    Text(value, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurface)
  }
}

@Composable
private fun AccessRow(check: AccessCheck?, checking: Boolean, targetValid: Boolean, onCheck: () -> Unit) {
  Row(
    Modifier.fillMaxWidth().heightIn(min = 56.dp).padding(start = Spacing.m, end = Spacing.s).testTag("access_check"),
    verticalAlignment = Alignment.CenterVertically,
  ) {
    Column(Modifier.weight(1f).padding(vertical = Spacing.s)) {
      Text(
        stringResource(R.string.row_access),
        style = MaterialTheme.typography.bodyMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
      )
      Spacer(Modifier.height(2.dp))
      Row(verticalAlignment = Alignment.CenterVertically) {
        if (check != null && !checking) {
          Box(
            Modifier.size(8.dp).background(
              accessCheckColor(check),
              CircleShape,
            ),
          )
          Spacer(Modifier.width(Spacing.s))
        }
        Text(
          when {
            checking -> stringResource(R.string.access_checking)
            !targetValid -> stringResource(R.string.target_invalid)
            check == null -> stringResource(R.string.access_unchecked)
            else -> accessCheckText(check)
          },
          style = MaterialTheme.typography.bodyLarge,
          color = MaterialTheme.colorScheme.onSurface,
        )
      }
    }
    if (checking) {
      CircularProgressIndicator(Modifier.padding(Spacing.m).size(20.dp), strokeWidth = 2.dp)
    } else {
      TextButton(onClick = onCheck, enabled = targetValid) { Text(stringResource(R.string.action_check)) }
    }
  }
}

@Composable
private fun PrimaryAction(state: EngineUiState, enabled: Boolean, onToggle: () -> Unit) {
  val modifier = Modifier.fillMaxWidth().height(56.dp).testTag("primary_action")
  when {
    state.canDisable -> FilledTonalButton(onClick = onToggle, modifier = modifier) {
      Text(stringResource(R.string.action_disable), style = MaterialTheme.typography.titleMedium)
    }
    state.canEnable -> Button(onClick = onToggle, enabled = enabled, modifier = modifier) {
      Text(
        stringResource(if (state.phase == EnginePhase.FAILED) R.string.action_retry else R.string.action_enable),
        style = MaterialTheme.typography.titleMedium,
      )
    }
    else -> Button(onClick = {}, enabled = false, modifier = modifier) {
      Row(horizontalArrangement = Arrangement.spacedBy(Spacing.s), verticalAlignment = Alignment.CenterVertically) {
        CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
        Text(
          stringResource(if (state.phase == EnginePhase.STARTING) R.string.status_starting else R.string.status_stopping),
          style = MaterialTheme.typography.titleMedium,
        )
      }
    }
  }
}
