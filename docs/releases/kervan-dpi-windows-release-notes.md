# Kervan DPI v1.0.1-rc2 — Windows release candidate (draft)

**Publication status: draft only. The earlier fix01 source was built and partially tested on Windows 11; the changed update source still needs a fresh native build and full QA. Do not publish or upload a Windows binary yet.** Suggested tag: `v1.0.1-rc2` (not created). Suggested GitHub title: **Kervan DPI v1.0.1-rc2 — Windows release candidate**. The public [release history](https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/releases) currently contains `v1.0.0` and `v1.0.1-rc1`; recheck tag availability before any approved publication.

## English

Fix 03 uses **MacallanTheRoot** as the application developer and Windows CompanyName, with `Copyright (c) 2026 MacallanTheRoot` in application LegalCopyright. These are file properties and do not establish an Authenticode signing identity. English and Turkish update status tests now select their locales explicitly; the changed source still requires a fresh native Windows build and QA.

**Kervan DPI** is the new application identity for the GoodbyeDPI Turkey desktop GUI. **Yol Açık, Kervan Yürür.** The approved minimalist blue camel is prepared for the window, tray and Windows EXE icon. The Windows application manages the bundled [GoodbyeDPI](https://github.com/ValdikSS/GoodbyeDPI) engine and [WinDivert](https://github.com/basil00/WinDivert) driver.

The proposed distribution is a portable `Kervan-DPI.exe` and a ZIP containing that EXE, English/Turkish guides and license notices. **No Windows artifact from this changed source exists yet.** No installer or Authenticode signature is claimed. Windows 11 x64 was tested on an **earlier prebranding build** (18/18 lifecycle scenarios); supported versions and final branded behavior must be set from new native QA of the exact artifact. No release download link or binary SHA-256 can be supplied before the build.

When the native candidate has passed QA, download its EXE or portable ZIP and matching `Kervan-DPI-1.0.1rc2-WINDOWS-SHA256SUMS.txt` from the project's release page. Verify each file with `Get-FileHash <file> -Algorithm SHA256`. Extract the ZIP into a stable folder you control and launch `Kervan-DPI.exe`; the application may request administrator permission through UAC to operate WinDivert. Select **Enable** to start and **Disable** to stop the engine. Closing the window hides it in the tray; choose **Quit Kervan DPI** to stop the active engine and exit. These instructions remain conditional until native verification.

Existing settings remain at `%APPDATA%\GoodbyeDPI-Turkey\config.json`. The application does not automatically rename or delete them. Back up the file and record an existing Startup shortcut target before an upgrade test. A legacy `GoodbyeDPI-Turkey GUI.lnk` can still point to the old EXE; see the [upgrade and rollback plan](../release/windows-migration.md). Retain the old EXE until the new build passes native upgrade and rollback QA. Portable removal should affect only the selected EXE/ZIP; there is no project installer or uninstaller.

Known limits: Kervan DPI is not a VPN, anonymity service or guarantee of access. The exact branded EXE still needs first-launch, icon/file-property, UAC, repeated Enable/Disable/Quit, Discord, ordinary HTTPS, post-Quit network, WinDivert path/process cleanup, `_MEI`, configuration, portable and legacy rollback QA. Defender/SmartScreen observations must be recorded factually. The camel artwork's redistribution rights and corresponding Qt/PySide6, GoodbyeDPI and WinDivert source provision remain publication gates. Linux SpoofDPI is a separately installed local proxy; transparent Zapret2/`nfqws2`/NFQUEUE is experimental and unreleased. Android and iOS have no downloads.

Preferences open from the header. Manual update checks run in the background and show official stable releases only. Manual updates open only the validated project release page. Automatic installation stays Off and unavailable pending a production publisher key and native after-exit helper QA; see the [update contract](../release/windows-update.md).

The existing [MIT application license](../../LICENSE) is separate from the [third-party notices](../../THIRD_PARTY_NOTICES.md) and [Windows dependency inventory](../release/windows-dependencies.md). Kervan DPI does not claim ownership or endorsement of GoodbyeDPI, WinDivert, SpoofDPI or Zapret2. Report issues through the project's [issue tracker](https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/issues) with the Windows build, artifact hash and redacted logs.

## Türkçe

Fix 03 ile uygulama geliştiricisi ve Windows CompanyName değeri **MacallanTheRoot**, uygulama LegalCopyright değeri `Copyright (c) 2026 MacallanTheRoot` oldu. Bu dosya bilgileri dijital imza kimliği oluşturmaz. İngilizce ve Türkçe güncelleme durum testleri yerel ayarlarını açıkça seçer; değişen kaynak için yeni yerel Windows derlemesi ve QA gereklidir.

**Kervan DPI**, GoodbyeDPI Turkey masaüstü arayüzünün yeni ürün kimliğidir. **Yol Açık, Kervan Yürür.** Windows sürümü, GoodbyeDPI ve WinDivert bileşenlerini yönetir. Onaylanan mavi deve simgesi hazırlanmıştır; gerçek Windows kabuğundaki görünümü henüz sınanmamıştır.

Önerilen dağıtım `Kervan-DPI.exe` ve bunu rehberler ile lisans bildirimleriyle birlikte taşıyan bir ZIP’tir. **Bu değişen kaynağa ait Windows dosyaları henüz üretilmedi.** Kurulum paketi ve uygulama için dijital imza yoktur. Önceki Windows 11 18/18 sonucu eski, marka öncesi derlemeye aittir. Desteklenen Windows sürümleri ve yayın kararı ancak son dosyanın yerel testinden sonra kesinleşir.

Doğrulanmış bir aday yayımlanırsa EXE veya taşınabilir ZIP’i proje sürüm sayfasından, eşleşen Windows SHA-256 listesiyle birlikte indirin. ZIP’i sabit bir klasöre çıkarın ve EXE’yi çalıştırın. WinDivert için UAC yönetici izni istenebilir. **Enable** başlatır, **Disable** durdurur; tepsi menüsündeki **Quit Kervan DPI** etkin motoru durdurup çıkar. Bu kullanım akışı son marka derlemesinde ayrıca doğrulanacaktır.

Ayarlar `%APPDATA%\GoodbyeDPI-Turkey\config.json` yolunda kalır; otomatik ad değiştirme veya silme yapılmaz. Yükseltmeden önce ayarları yedekleyin ve eski başlangıç kısayolunun hedefini kaydedin. Eski EXE’yi geri dönüş testi tamamlanana kadar saklayın. [Göç ve geri dönüş planı](../release/windows-migration.md) ayrıntıları açıklar. Taşınabilir dosyayı kaldırmak kişisel ayarların veya paylaşılan WinDivert durumunun silinmesi anlamına gelmez.

Tercihler üst başlıktan açılır. Elle güncelleme denetimi arka planda çalışır ve yalnızca resmi kararlı sürümleri gösterir. Elle güncelleme doğrulanan proje sürüm sayfasını açar. Üretim yayıncı anahtarı ve yerel Windows yardımcı program QA tamamlanmadan otomatik yükleme Kapalı ve kullanılamaz durumdadır. [Güncelleme sözleşmesi](../release/windows-update.md).

Kervan DPI VPN ya da anonimlik aracı değildir ve her ağda erişim vaat etmez. Son Windows EXE’sinin yaşam döngüsü, bağlantı, `_MEI`, kısayol, ayar ve geri dönüş testleri beklemektedir. Deve görselinin dağıtım hakları ve sürümle eşleşen üçüncü taraf kaynakları da doğrulanmalıdır. Linux şeffaf NFQUEUE çalışması deneysel ve yayımlanmamıştır; Android/iOS uygulaması bulunmaz. Uygulama MIT lisansı ve bağımsız bileşenlerin lisansları için yukarıdaki bildirimlere bakın.

## Artifact and approval gate

| Proposed file | Current status |
| --- | --- |
| `Kervan-DPI.exe` | **PENDING native Windows build and QA** |
| `Kervan-DPI-1.0.1rc2-windows-portable.zip` | **PENDING native Windows build and QA** |
| `Kervan-DPI-1.0.1rc2-WINDOWS-SHA256SUMS.txt` | **PENDING genuine EXE/ZIP** |
| `Kervan-DPI-1.0.1rc2-windows-rc-build-source.zip` | Local build handoff exists; its exact hash is in the adjacent `Kervan-DPI-1.0.1rc2-SOURCE-SHA256SUMS.txt`. It is source, not a Windows EXE. |

Use the [native QA checklist](../release/windows-qa-checklist.md) and [report template](../release/windows-native-qa-report-template.md). Fill the supported Windows versions, EXE/ZIP checksums, build provenance, native results and rights/source evidence **before** requesting explicit publication approval. Do not attach an absent artifact or mark this draft stable.
