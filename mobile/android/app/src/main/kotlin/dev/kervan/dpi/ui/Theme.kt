package dev.kervan.dpi.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

/*
 * Kervan brand scheme. One blue (the desktop Fix04 accent #315FA7, the camel's
 * hue) on cool graphite neutrals taken from the desktop tokens
 * (docs/ui-redesign-spec.md). Hex values live only in this file.
 */
private val Light = lightColorScheme(
  primary = Color(0xFF315FA7),
  onPrimary = Color(0xFFFFFFFF),
  primaryContainer = Color(0xFFD9E3F6),
  onPrimaryContainer = Color(0xFF0F2F5E),
  secondary = Color(0xFF526174),
  onSecondary = Color(0xFFFFFFFF),
  secondaryContainer = Color(0xFFE1E7EF),
  onSecondaryContainer = Color(0xFF192434),
  tertiary = Color(0xFF526174),
  onTertiary = Color(0xFFFFFFFF),
  background = Color(0xFFF6F7F9),
  onBackground = Color(0xFF192434),
  surface = Color(0xFFF6F7F9),
  onSurface = Color(0xFF192434),
  surfaceVariant = Color(0xFFE1E7EF),
  onSurfaceVariant = Color(0xFF526174),
  surfaceContainerLowest = Color(0xFFFFFFFF),
  surfaceContainerLow = Color(0xFFFFFFFF),
  surfaceContainer = Color(0xFFEDF1F5),
  surfaceContainerHigh = Color(0xFFE7ECF1),
  surfaceContainerHighest = Color(0xFFE1E7EF),
  outline = Color(0xFF7A8899),
  outlineVariant = Color(0xFFD8E0E8),
  error = Color(0xFFB33F49),
  onError = Color(0xFFFFFFFF),
  errorContainer = Color(0xFFF9DEE0),
  onErrorContainer = Color(0xFF5C1219),
  inverseSurface = Color(0xFF2B3541),
  inverseOnSurface = Color(0xFFEEF2F6),
  inversePrimary = Color(0xFF91B4F0),
)

private val Dark = darkColorScheme(
  primary = Color(0xFF91B4F0),
  onPrimary = Color(0xFF17263A),
  primaryContainer = Color(0xFF244A86),
  onPrimaryContainer = Color(0xFFD9E3F6),
  secondary = Color(0xFFB6C1CE),
  onSecondary = Color(0xFF1B222B),
  secondaryContainer = Color(0xFF2B3541),
  onSecondaryContainer = Color(0xFFEEF2F6),
  tertiary = Color(0xFFB6C1CE),
  onTertiary = Color(0xFF1B222B),
  background = Color(0xFF11161D),
  onBackground = Color(0xFFEEF2F6),
  surface = Color(0xFF11161D),
  onSurface = Color(0xFFEEF2F6),
  surfaceVariant = Color(0xFF2B3541),
  onSurfaceVariant = Color(0xFFB6C1CE),
  surfaceContainerLowest = Color(0xFF0C1016),
  surfaceContainerLow = Color(0xFF1B222B),
  surfaceContainer = Color(0xFF1F2731),
  surfaceContainerHigh = Color(0xFF222B35),
  surfaceContainerHighest = Color(0xFF2B3541),
  outline = Color(0xFF8593A3),
  outlineVariant = Color(0xFF3B4857),
  error = Color(0xFFF08A92),
  onError = Color(0xFF4A0C12),
  errorContainer = Color(0xFF6B1F27),
  onErrorContainer = Color(0xFFF9DEE0),
  inverseSurface = Color(0xFFEEF2F6),
  inverseOnSurface = Color(0xFF192434),
  inversePrimary = Color(0xFF315FA7),
)

/** Semantic status colour; same meaning everywhere, never taken from content. */
@Immutable
data class StatusColors(val active: Color, val inactive: Color)

private val LightStatus = StatusColors(active = Color(0xFF207759), inactive = Color(0xFF6D7A89))
private val DarkStatus = StatusColors(active = Color(0xFF73D2AA), inactive = Color(0xFF94A3B5))
private val LocalStatusColors = staticCompositionLocalOf { LightStatus }

/** 8dp spacing scale used by every screen. */
object Spacing {
  val xs = 4.dp
  val s = 8.dp
  val m = 16.dp
  val l = 24.dp
  val xl = 32.dp
}

private val base = Typography()
private val KervanType = base.copy(
  headlineMedium = base.headlineMedium.copy(fontWeight = FontWeight.Medium),
  titleLarge = base.titleLarge.copy(fontWeight = FontWeight.Medium),
  titleSmall = base.titleSmall.copy(fontWeight = FontWeight.Medium),
)

object KervanTheme {
  val status: StatusColors
    @Composable @ReadOnlyComposable get() = LocalStatusColors.current
}

@Composable
fun KervanTheme(dark: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
  CompositionLocalProvider(LocalStatusColors provides if (dark) DarkStatus else LightStatus) {
    MaterialTheme(colorScheme = if (dark) Dark else Light, typography = KervanType, content = content)
  }
}
