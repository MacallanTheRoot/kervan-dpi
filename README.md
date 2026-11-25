<div align="center">

<img src="site/assets/kervan-camel.png" alt="Kervan DPI blue camel logo" width="116" />

# Kervan DPI

**Yol Açık, Kervan Yürür.**  
*The road stays open, the caravan moves on.*

Open-source tools for navigating network restrictions caused by Deep Packet Inspection (DPI).

[🌐 Website](https://macallantheroot.github.io/kervan-dpi/) · [📦 Releases](https://github.com/MacallanTheRoot/kervan-dpi/releases) · [🐛 Issues](https://github.com/MacallanTheRoot/kervan-dpi/issues)

**[Türkçe](#türkçe) | [English](#english)**

</div>

> [!IMPORTANT]
> Kervan DPI is experimental software. Success varies by network and platform. It is not an anonymity service, does not hide your public IP address, and does not guarantee access to any particular website.  
> Kervan DPI deneysel bir yazılımdır. Başarı ağa ve platforma göre değişir. Anonimlik sağlamaz, genel IP adresinizi gizlemez ve hiçbir siteye erişimi garanti etmez.

---

<a id="türkçe"></a>
## 🇹🇷 Türkçe

### Kervan DPI nedir?

**Kervan DPI**, bazı ağlarda erişim kısıtlamalarını uygulamak için kullanılan **Derin Paket İncelemesi (DPI)** yöntemlerine karşı yerel çözümler sunan açık kaynaklı bir projedir. Platformlara göre farklı motorlar ve arayüzler kullanır. Amaç, mevcut teknolojileri anlaşılır bir deneyimde birleştirmektir; her ağda çalışan tek bir yöntem sunduğumuz iddia edilmez.

### Platform durumu

| Platform | Durum | Sürüm / erişim |
| --- | --- | --- |
| **Android** | ✅ **Herkese açık deneysel beta** | [0.2.0-beta1 sürüm notları](https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/android-v0.2.0-beta1) · [APK indir](https://github.com/MacallanTheRoot/kervan-dpi/releases/download/android-v0.2.0-beta1/Kervan-DPI-Android-0.2.0-beta1-universal.apk) |
| **Windows** | ✅ **Herkese açık sürüm adayı (RC)** | [v1.0.1-rc2 ve indirmeler](https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/v1.0.1-rc2) |
| **Linux** | 🛠️ Yeni nesil sürüm geliştirme / test aşamasında | Yeni Kervan Linux paketi henüz yayımlanmadı¹ |
| **iOS** | 🧪 Gerçek cihazda geliştirme sürümü denendi | Herkese açık IPA / TestFlight yok |
| **Web sitesi** | ✅ Yayında | [Resmî web sitesi](https://macallantheroot.github.io/kervan-dpi/) |

¹ Eski [v1.0.1-rc1](https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/v1.0.1-rc1) sürümünde *GoodbyeDPI Turkey* adıyla Linux dosyaları bulunur. Bunlar geliştirilmekte olan yeni Kervan Linux motorunun yayımlanmış sürümü **değildir**.

### Android kurulumu

**Gereksinimler:** Android 10 veya üzeri; **arm64-v8a** ya da **x86_64**. 32-bit ARM desteklenmez.

1. [İmzalı Android beta APK'sını indirin](https://github.com/MacallanTheRoot/kervan-dpi/releases/download/android-v0.2.0-beta1/Kervan-DPI-Android-0.2.0-beta1-universal.apk).
2. İndirme bütünlüğünü sürüm sayfasındaki `SHA256SUMS` ile kontrol edin.
3. APK'yı açıp Android'in kurulum iznini onaylayın. İşiniz bitince tarayıcıya verdiğiniz bilinmeyen uygulama yükleme iznini geri alabilirsiniz.
4. Uygulamada **Aç** düğmesine dokunun ve Android'in VPN iznini onaylayın.

**Android neden VPN izni istiyor?** Kervan, Android `VpnService` arayüzünü trafiği **cihazın üzerindeki yerel DPI motoruna** yönlendirmek için kullanır; uzak bir VPN sunucusuna bağlandığını iddia etmez. Aynı anda yalnızca bir Android VPN etkin olabilir.

Daha önce geliştirme amaçlı **debug** derlemesi kurduysanız imza uyuşmazlığı nedeniyle doğrudan güncelleme başarısız olabilir. Eski uygulamayı kaldırmak yerel ayarlarını silebilir; önce [sürüm notlarını](https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/android-v0.2.0-beta1) okuyun.

### Windows kurulumu

1. [v1.0.1-rc2 sürüm sayfasını](https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/v1.0.1-rc2) açın.
2. Windows x64 için `Kervan-DPI.exe` veya taşınabilir ZIP'i indirin.
3. Yayımlanan SHA-256 kontrol dosyasıyla indirmeyi doğrulayın; ardından uygulamayı çalıştırın.

Windows sürümü **GoodbyeDPI** ve **WinDivert** bileşenlerini içerir ve yönetici yetkisi gerektirebilir. Bu bir **release candidate**'tır, kararlı sürüm değildir. EXE **dijital olarak imzalanmamıştır**; Windows güvenlik uyarısı gösterebilir. Otomatik testler başarılı olsa da bu derlemenin kapsamlı gerçek Windows ortamı doğrulaması tamamlanmamıştır.

### Diğer platformlar

**Linux:** Yeni uygulama yolu yerel test ve geliştirme aşamasındadır; henüz indirilebilir güncel Kervan Linux sürümü yoktur. Eski SpoofDPI tabanlı paketleri yeni sistem geneli motorla karıştırmayın.

**iOS:** iPhone 14 Pro üzerinde yerel bir geliştirme sürümü denenmiştir; ancak DPI engelini aşma başarısı bu cihazda kanıtlanmamıştır. Genel dağıtıma uygun IPA veya TestFlight bağlantısı yayımlanmamıştır.

### Gizlilik ve sınırlar

- **Her ağda çalışacağı garanti değildir.** Android'de belirli bir engelli site için kısıtlı sayıda ağda erişim gözlenmiştir; bu evrensel başarı anlamına gelmez.
- **Anonimlik sağlamaz, IP adresinizi gizlemez ve trafiğe ek uçtan uca şifreleme getirmez.**
- **Android VPN izni**, yalnızca yerel paket işleme yolunun bir parçasıdır; başka bir VPN aynı anda etkin olamaz.
- Android beta için QUIC/UDP, çalışırken ağ değiştirme, motor çökmesinden kurtulma ve çok uzun süreli kullanım yeterince doğrulanmamıştır.
- Android'deki yerel SOCKS5 dinleyicisinin kimlik doğrulaması yoktur; aynı cihazdaki başka uygulamalar, motor çalışırken bu yerel adrese bağlanabilir.
- Bu projedeki her platformun teknik yapısı, kapsamı ve sürüm olgunluğu farklıdır.

Android'in ayrıntılı teknik notları ve derleme talimatları: [Android kaynak ve README](https://github.com/MacallanTheRoot/kervan-dpi/blob/android-v0.2.0-beta1/mobile/README.md).

### Açık kaynak, lisans ve katkı

Kervan DPI'ın proje kodu [MIT lisansı](LICENSE) kapsamında sunulur. Dahil edilen veya bağlantı verilen **GoodbyeDPI, WinDivert, Qt/PySide6, GSAP ve diğer üçüncü taraf bileşenler** kendi lisans ve kullanım koşullarına tabidir. [Masaüstü üçüncü taraf bildirimleri](THIRD_PARTY_NOTICES.md) ve [Android beta üçüncü taraf bildirimleri](https://github.com/MacallanTheRoot/kervan-dpi/releases/download/android-v0.2.0-beta1/THIRD-PARTY-NOTICES-Android.txt) ayrı sağlanır. Mavi deve marka görselinin MIT kapsamında lisanslandığı iddia edilmez.

Geliştirici: **[MacallanTheRoot](https://github.com/MacallanTheRoot)**. Hata bildirimi, öneri ve katkılar için [GitHub Issues](https://github.com/MacallanTheRoot/kervan-dpi/issues) sayfasını kullanabilirsiniz.

**Yol Açık, Kervan Yürür.** 🐪

---

<a id="english"></a>
## 🇬🇧 English

### What is Kervan DPI?

**Kervan DPI** is an open-source project offering local approaches to restrictions enforced using **Deep Packet Inspection (DPI)** on some networks. Different platforms use different engines and interfaces. The goal is to make these technologies easier to use—not to claim one technique works everywhere.

### Platform status

| Platform | Status | Version / access |
| --- | --- | --- |
| **Android** | ✅ **Public experimental beta** | [0.2.0-beta1 release notes](https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/android-v0.2.0-beta1) · [Download APK](https://github.com/MacallanTheRoot/kervan-dpi/releases/download/android-v0.2.0-beta1/Kervan-DPI-Android-0.2.0-beta1-universal.apk) |
| **Windows** | ✅ **Public release candidate (RC)** | [v1.0.1-rc2 and downloads](https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/v1.0.1-rc2) |
| **Linux** | 🛠️ Next-generation build under development / testing | No current Kervan Linux package released¹ |
| **iOS** | 🧪 Development build tested on a physical device | No public IPA or TestFlight release |
| **Website** | ✅ Live | [Official website](https://macallantheroot.github.io/kervan-dpi/) |

¹ Historical Linux binaries are available under the older *GoodbyeDPI Turkey* name in [v1.0.1-rc1](https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/v1.0.1-rc1). They are **not** a public release of the newer Kervan Linux engine.

### Install on Android

**Requirements:** Android 10 or later, **arm64-v8a** or **x86_64**. 32-bit ARM is not supported.

1. [Download the signed Android beta APK](https://github.com/MacallanTheRoot/kervan-dpi/releases/download/android-v0.2.0-beta1/Kervan-DPI-Android-0.2.0-beta1-universal.apk).
2. Check the download against the release's `SHA256SUMS` file.
3. Open the APK and approve Android's installation prompt. You can revoke the browser's install-unknown-apps permission afterward.
4. Tap **Turn on** in Kervan and approve Android's VPN permission prompt.

**Why does Android request VPN permission?** Kervan uses the Android `VpnService` interface to route traffic into a **local DPI engine on the device**. It does not claim to connect to a remote VPN server. Android allows only one active VPN at a time.

If you previously installed a **debug** build, Android may reject an in-place update due to a different signing certificate. Uninstalling the old build can erase its local settings; read the [release notes](https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/android-v0.2.0-beta1) first.

### Install on Windows

1. Open the [v1.0.1-rc2 release page](https://github.com/MacallanTheRoot/kervan-dpi/releases/tag/v1.0.1-rc2).
2. Download `Kervan-DPI.exe` or the portable ZIP for Windows x64.
3. Verify the download using the published SHA-256 checksum file, then run the application.

The Windows release bundles **GoodbyeDPI** and **WinDivert** and may require administrator privileges. This is a **release candidate**, not a stable release. The EXE is **not code-signed**, so Windows may show a security warning. Automated tests passed, but comprehensive native Windows-session validation of this specific build is still outstanding.

### Other platforms

**Linux:** The newer implementation remains in local testing and development; no current Kervan Linux binary is publicly available. Do not confuse historical SpoofDPI-based packages with the newer system-wide engine.

**iOS:** A development build was tested on an iPhone 14 Pro, but DPI circumvention was not conclusively demonstrated on that device. No publicly distributable IPA or TestFlight link is available.

### Privacy and limitations

- **No universal bypass guarantee.** An access improvement was observed for a particular blocked site on a limited set of Android networks; that does not establish success elsewhere.
- **No anonymity, IP-address hiding, or additional end-to-end encryption.**
- On **Android**, VPN permission enables local traffic handling; another VPN cannot be active simultaneously.
- QUIC/UDP, live network switching, engine-crash recovery, and extended-duration operation are not adequately device-tested in this Android beta.
- The Android engine's local SOCKS5 listener has no authentication; another app on the same device may be able to connect while it is running.
- Technical approaches, capabilities, and maturity differ across platforms.

Android technical notes and build instructions: [Android source and README](https://github.com/MacallanTheRoot/kervan-dpi/blob/android-v0.2.0-beta1/mobile/README.md).

### Open source, licenses, and contributing

Kervan DPI's project code is available under the [MIT License](LICENSE). Bundled or referenced **GoodbyeDPI, WinDivert, Qt/PySide6, GSAP, and other third-party components** have their own license terms. See the [desktop third-party notices](THIRD_PARTY_NOTICES.md) and [Android beta third-party notices](https://github.com/MacallanTheRoot/kervan-dpi/releases/download/android-v0.2.0-beta1/THIRD-PARTY-NOTICES-Android.txt). The blue camel brand artwork is not claimed to be MIT-licensed.

Developer: **[MacallanTheRoot](https://github.com/MacallanTheRoot)**. Please use [GitHub Issues](https://github.com/MacallanTheRoot/kervan-dpi/issues) for bug reports, feedback, and contributions.

**Yol Açık, Kervan Yürür.** 🐪
