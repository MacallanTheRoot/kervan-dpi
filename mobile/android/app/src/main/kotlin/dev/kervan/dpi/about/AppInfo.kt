package dev.kervan.dpi.about

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.widget.Toast
import dev.kervan.dpi.R

/** The facts About shows. Name and slogan are string resources; versions come from the installed package. */
object AppInfo {
  const val DEVELOPER = "MacallanTheRoot"
  const val DEVELOPER_URL = "https://github.com/macallanTheRoot"
  const val REPOSITORY_URL = "https://github.com/MacallanTheRoot/kervan-dpi"
  const val LICENSE_URL = "https://github.com/MacallanTheRoot/kervan-dpi/blob/main/LICENSE"

  data class Version(val name: String, val code: Long)

  fun version(context: Context): Version {
    val info = context.packageManager.getPackageInfo(context.packageName, 0)
    return Version(info.versionName ?: "?", info.longVersionCode)
  }

  fun platform(): String = "Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})"

  /**
   * Opens [url] with ACTION_VIEW. The selector resolves it like a plain web link, so the
   * browser gets it even when another app claims that site.
   */
  fun openInBrowser(context: Context, url: String) {
    val view = Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    val browser = Intent(view).apply {
      selector = Intent(Intent.ACTION_VIEW, Uri.fromParts("https", "", null)).addCategory(Intent.CATEGORY_BROWSABLE)
    }
    for (intent in listOf(browser, view)) {
      try {
        context.startActivity(intent)
        return
      } catch (_: ActivityNotFoundException) {
        // Try the next form.
      }
    }
    Toast.makeText(context, R.string.no_browser, Toast.LENGTH_LONG).show()
  }

  fun share(context: Context, text: String) {
    val send = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text)
    context.startActivity(Intent.createChooser(send, null))
  }

  fun acknowledgements(context: Context): String =
    context.resources.openRawResource(R.raw.acknowledgements).bufferedReader().use { it.readText() }
}
