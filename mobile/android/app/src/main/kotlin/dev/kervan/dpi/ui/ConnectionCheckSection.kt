package dev.kervan.dpi.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import dev.kervan.dpi.R
import dev.kervan.dpi.engine.AccessCheck
import dev.kervan.dpi.probe.AccessTarget
import dev.kervan.dpi.probe.CheckSettings

/** Everything the connection check section shows and does. */
data class CheckUi(
  val settings: CheckSettings,
  val result: AccessCheck?,
  val checking: Boolean,
  /** False while the engine starts or stops: a result would belong to neither state. */
  val engineSettled: Boolean,
  val onChange: (CheckSettings) -> Unit,
  val onCheck: () -> Unit,
) {
  val canCheck get() = settings.target != null && !checking && engineSettled
}

/** Target selection and a check that can run with Kervan on or off. */
@Composable
fun ConnectionCheckSection(check: CheckUi) {
  val custom = check.settings.key == AccessTarget.CUSTOM_KEY
  Column {
    SectionHeader(stringResource(R.string.section_check))
    Group {
      for (t in AccessTarget.BUILT_IN) {
        RadioRow(t.label, t.host, selected = check.settings.key == t.key, tag = "target_${t.key}") {
          check.onChange(check.settings.copy(key = t.key))
        }
      }
      RadioRow(
        stringResource(R.string.target_custom), stringResource(R.string.target_custom_sum),
        selected = custom, tag = "target_custom",
      ) { check.onChange(check.settings.copy(key = AccessTarget.CUSTOM_KEY)) }
      if (custom) {
        val invalid = check.settings.customText.isNotBlank() && check.settings.target == null
        OutlinedTextField(
          value = check.settings.customText,
          onValueChange = { check.onChange(check.settings.copy(customText = it)) },
          singleLine = true,
          isError = invalid,
          label = { Text(stringResource(R.string.target_custom)) },
          supportingText = {
            Text(stringResource(if (invalid) R.string.target_custom_error else R.string.target_custom_hint))
          },
          keyboardOptions = KeyboardOptions(
            capitalization = KeyboardCapitalization.None, autoCorrectEnabled = false, keyboardType = KeyboardType.Uri,
          ),
          modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.m, vertical = Spacing.s).testTag("custom_target"),
        )
      }
    }
    Note(stringResource(R.string.check_note))
    if (check.result != null) {
      Row(
        Modifier
          .padding(start = Spacing.m, end = Spacing.m, top = Spacing.m)
          .testTag("check_result")
          .semantics(mergeDescendants = true) { liveRegion = LiveRegionMode.Polite },
        verticalAlignment = Alignment.CenterVertically,
      ) {
        Box(Modifier.size(8.dp).background(accessCheckColor(check.result), CircleShape))
        Spacer(Modifier.width(Spacing.s))
        Column {
          Text(accessCheckText(check.result), style = MaterialTheme.typography.bodyLarge)
          Text(
            accessCheckEngine(check.result),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
          )
        }
      }
    }
    OutlinedButton(
      onClick = check.onCheck,
      enabled = check.canCheck,
      modifier = Modifier.fillMaxWidth().padding(top = Spacing.m).heightIn(min = 48.dp).testTag("check_now"),
    ) {
      if (check.checking) {
        CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
        Spacer(Modifier.width(Spacing.s))
      }
      Text(stringResource(if (check.checking) R.string.access_checking else R.string.action_check_now))
    }
  }
}
