package dev.kervan.dpi.about

import java.io.File
import javax.xml.parsers.DocumentBuilderFactory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Reads the resource files; Gradle runs unit tests in the module directory. */
class AboutTest {
  private fun strings(dir: String): Map<String, Pair<String, Boolean>> {
    val nodes = DocumentBuilderFactory.newInstance().newDocumentBuilder()
      .parse(File("src/main/res/$dir/strings.xml")).getElementsByTagName("string")
    return (0 until nodes.length).map { nodes.item(it) }.associate {
      it.attributes.getNamedItem("name").nodeValue to
        (it.textContent to (it.attributes.getNamedItem("translatable")?.nodeValue != "false"))
    }
  }

  private val en = strings("values")
  private val tr = strings("values-tr")

  @Test
  fun identity() {
    assertEquals("Kervan DPI", en.getValue("app_name").first)
    assertEquals("Yol Açık, Kervan Yürür.", en.getValue("slogan").first)
    assertEquals("MacallanTheRoot", AppInfo.DEVELOPER)
    assertEquals("https://github.com/macallanTheRoot", AppInfo.DEVELOPER_URL)
    assertEquals("https://github.com/MacallanTheRoot/kervan-dpi", AppInfo.REPOSITORY_URL)
  }

  @Test
  fun englishAndTurkishHaveTheSameStringsAndPlaceholders() {
    val translatable = en.filterValues { it.second }
    assertEquals(translatable.keys, tr.keys)
    val placeholder = Regex("%\\d\\$[sd]")
    for ((name, value) in translatable) {
      fun of(s: String) = placeholder.findAll(s).map { it.value }.sorted().toList()
      assertEquals(name, of(value.first), of(tr.getValue(name).first))
    }
  }

  @Test
  fun noTextClaimsBypassOrNamesDiscord() {
    for ((name, value) in en + tr.mapKeys { "tr/${it.key}" }) {
      val text = value.first.lowercase()
      for (claim in listOf("discord", "bypass", "unblock", "vpn active")) assertFalse("$name: $text", claim in text)
    }
  }

  @Test
  fun acknowledgementsCoverEveryPinnedEngineCommit() {
    val notices = File("src/main/res/raw/acknowledgements.txt").readText()
    val pinned = Regex("`([0-9a-f]{40})`").findAll(File("../../core/third_party/README.md").readText())
      .map { it.groupValues[1] }.toList()
    assertTrue(pinned.isNotEmpty())
    for (commit in pinned) assertTrue(commit, commit in notices)
    assertTrue("Apache License" in notices)
  }
}
