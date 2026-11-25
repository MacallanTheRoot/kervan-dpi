package dev.kervan.dpi.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import dev.kervan.dpi.R
import dev.kervan.dpi.engine.AccessCheck
import dev.kervan.dpi.probe.CheckOutcome

@Composable
fun accessCheckText(check: AccessCheck): String = when (check.outcome) {
  CheckOutcome.VERIFIED -> stringResource(R.string.access_verified, check.host, check.time)
  CheckOutcome.ANSWERED -> stringResource(R.string.access_answered, check.host, check.time)
  CheckOutcome.REDIRECTED -> stringResource(R.string.access_redirected, check.host, check.time)
  CheckOutcome.OTHER_STATUS -> stringResource(R.string.access_other_status, check.host, check.time, check.status ?: 0)
  CheckOutcome.OTHER_REPLY -> stringResource(R.string.access_other_reply, check.host, check.time)
  CheckOutcome.UNTRUSTED -> stringResource(R.string.access_untrusted, check.host, check.time)
  CheckOutcome.NAME_NOT_RESOLVED -> stringResource(R.string.access_dns, check.host, check.time)
  CheckOutcome.NO_ANSWER -> stringResource(R.string.access_fail, check.host, check.time)
}

@Composable
fun accessCheckEngine(check: AccessCheck): String =
  stringResource(if (check.engineOn) R.string.check_engine_on else R.string.check_engine_off)

/** Green only for a recognised reply; a custom address's unchecked answer stays neutral. */
@Composable
fun accessCheckColor(check: AccessCheck): Color = when {
  check.outcome == CheckOutcome.VERIFIED -> KervanTheme.status.active
  check.outcome.ok -> KervanTheme.status.inactive
  else -> MaterialTheme.colorScheme.error
}
