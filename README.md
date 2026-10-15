# Kervan DPI

![Kervan DPI mavi deve simgesi / blue camel mark](site/assets/kervan-camel.png)

**Yol Açık, Kervan Yürür.**

Kervan DPI, Windows ve Linux için açık kaynaklı bir masaüstü uygulamasıdır. DPI kaynaklı erişim kısıtlamalarına yönelik araçları tek arayüzden yönetir. Windows'ta GoodbyeDPI, Linux'ta ise ayrı kurulan SpoofDPI ile çalışır.

[Kaynak kod](https://github.com/MacallanTheRoot/kervan-dpi) · [İndir / Releases](https://github.com/MacallanTheRoot/kervan-dpi/releases) · [Web sitesi (yayına hazırlanıyor)](https://macallantheroot.github.io/kervan-dpi/)

## Türkçe

### Windows ve Linux

**Windows:** Yayımlanmış sürüm, GoodbyeDPI motorunu WinDivert ile çalıştırır. Masaüstü arayüzünden motoru başlatıp durdurabilir, DNS seçimini değiştirebilir, durumu ve etkinlik günlüğünü izleyebilirsiniz. WinDivert için yönetici izni istenebilir.

**Linux:** Yayımlanmış sürüm, ayrıca yüklenmesi gereken SpoofDPI'yi yerel HTTP proxy olarak yönetir. Proxy 127.0.0.1:8080 adresini kullanır; tarayıcı veya diğer uygulamalar bu proxy'yi kullanacak şekilde ayarlanmalıdır. Uygulama sistemin proxy ayarlarını kendiliğinden değiştirmez. İsteğe bağlı şeffaf, sistem genelinde çalışma desteği geliştirilmektedir; mevcut indirmelerde yer almaz.

### Özellikler

- **Enable / Disable** ile desteklenen motoru arayüzden başlatma ve durdurma.
- DNS sağlayıcısı seçimi, bağlantı durumu ve etkinlik günlüğü.
- Desteklenen masaüstlerinde sistem tepsisi; açık, koyu ve sistem temasına uyumlu görünüm.
- Windows ve Linux'un farklı çalışma biçimlerini tek bir Qt arayüzünde sunma.

Sonuçlar ağa ve kullanılan motora bağlıdır. Kervan DPI bir VPN, anonimlik, şifreleme veya IP gizleme hizmeti değildir; her ağda erişim sağlayacağını garanti etmez.

### İndirme ve kurulum

[GitHub Releases](https://github.com/MacallanTheRoot/kervan-dpi/releases) sayfasındaki **v1.0.1-rc1 ön sürümü**, Windows x86_64 EXE, Linux amd64 DEB ve Linux amd64 TAR.GZ dosyalarını içerir. Bu yayımlanmış dosyalar eski **GoodbyeDPI Turkey** adlarını taşır; daha yeni Kervan markalı uygulama paketleri henüz yayımlanmamıştır.

| Platform | Yayımlanmış dosya | Kullanım |
| --- | --- | --- |
| Windows x86_64 | GoodbyeDPI-Turkey-1.0.1rc1-windows-x86_64.exe | EXE'yi indirin ve çalıştırın. |
| Debian / Kali Linux amd64 | goodbyedpi-turkey_1.0.1.rc1_amd64.deb | Paketi kurun, ardından uygulamayı açın. |
| Linux amd64 taşınabilir | GoodbyeDPI-Turkey-1.0.1rc1-linux-amd64.tar.gz | Arşivi açın ve içindeki uygulamayı çalıştırın. |

DEB dosyasını indirdiğiniz dizinde kurmak için:

~~~sh
sudo apt install ./goodbyedpi-turkey_1.0.1.rc1_amd64.deb
goodbyedpi-turkey
~~~

Linux'ta [SpoofDPI](https://github.com/xvzc/SpoofDPI) ayrıca kurulmalı ve çalıştırılabilir dosyası uygulamanın bulabileceği bir konumda olmalıdır. Bir yöntem, Go kuruluysa şudur:

~~~sh
go install github.com/xvzc/SpoofDPI/cmd/spoofdpi@v0.12.0
~~~

Ardından kullanacağınız tarayıcıyı veya uygulamayı 127.0.0.1:8080 HTTP proxy'sine yönlendirin. Yayımlanmış paketlere ilişkin ek notlar için [Linux paketleme belgesine](docs/packaging-rc.md) bakın. İndirme sayfasındaki SHA256SUMS dosyasıyla dosyaların bütünlüğünü doğrulayabilirsiniz.

### Teknik yapı

Arayüz Python, PySide6 ve Qt Widgets ile yazılmıştır. Windows sürümü GoodbyeDPI ve WinDivert kullanır; Linux sürümü ise kullanıcı oturumunda çalışan harici SpoofDPI proxy'sini yönetir. Bu motorların izinleri ve ağdaki etkileri farklıdır. Geliştirilmekte olan şeffaf Linux desteği, yayımlanmış proxy sürümünden ayrı bir çalışma yoludur.

Eski paket ve ayar kimlikleri uyumluluk için korunur: Linux komutu ve paket adı goodbyedpi-turkey, Linux ayar yolu $XDG_CONFIG_HOME/goodbyedpi-turkey/config.json (XDG_CONFIG_HOME tanımlı değilse ~/.config/goodbyedpi-turkey/config.json), Windows ayar yolu %APPDATA%\GoodbyeDPI-Turkey\config.json.

### Neden Kervan?

Bir kervan, yolu kapanınca yolculuğu bırakmaz; ilerlemek için başka bir yol arar. Kervan adı, DPI kaynaklı erişim kısıtlamaları karşısında çözüm arama kararlılığını anlatır. **Yol Açık, Kervan Yürür.**

### Açık kaynak ve katkı

Kaynak kodu [GitHub deposunda](https://github.com/MacallanTheRoot/kervan-dpi) inceleyebilir, hata bildirimlerini ve önerileri [Issues](https://github.com/MacallanTheRoot/kervan-dpi/issues) üzerinden paylaşabilirsiniz. Geliştirici: [MacallanTheRoot](https://github.com/MacallanTheRoot).

Uygulama kodu [MIT lisansı](LICENSE) altındadır. GoodbyeDPI, WinDivert ve SpoofDPI bağımsız projelerdir; geliştirilmekte olan Linux yolunda kullanılan [Zapret2](https://github.com/bol-van/zapret2) de ayrı bir upstream projedir. Her birinin kendi lisansı geçerlidir. [Üçüncü taraf bildirimleri](THIRD_PARTY_NOTICES.md), [Qt/PySide6 LGPL kaynak ve yeniden bağlama bilgileri](docs/qt-lgpl-compliance.md) ve [web sitesi kaynak notları](site/README.md) ayrıca sağlanır.

Web sitesinde kullanılan GSAP, uygulamanın MIT lisansına dahil değildir; [GSAP Standard License bildirimi](site/vendor/gsap/NOTICE.md) ayrıdır. Mavi deve görseli proje sahibinin isteğiyle bu proje için ChatGPT üzerinden üretilmiş ve onaylanmıştır; burada MIT lisanslı olduğu iddia edilmez.

## English

### Overview

Kervan DPI is an open-source desktop application for Windows and Linux. It brings controls for DPI circumvention tools into one interface: GoodbyeDPI on Windows and a separately installed SpoofDPI proxy on Linux.

[Source code](https://github.com/MacallanTheRoot/kervan-dpi) · [Downloads](https://github.com/MacallanTheRoot/kervan-dpi/releases) · [Website (publication in preparation)](https://macallantheroot.github.io/kervan-dpi/)

### Windows and Linux

**Windows:** The published build runs GoodbyeDPI with WinDivert. The desktop interface lets you start and stop the engine, choose DNS settings, and view status and activity. WinDivert may require administrator permission.

**Linux:** The published build manages SpoofDPI as a local HTTP proxy. Install SpoofDPI separately, then configure each browser or application that should use the proxy at 127.0.0.1:8080. Kervan DPI does not change system proxy settings automatically. Optional transparent, system-wide support is in development and is not part of the current downloads.

### Features

- Start and stop the supported engine with **Enable / Disable**.
- Choose a DNS provider and inspect status and the activity log.
- Use the system tray on supported desktops and select light, dark, or system appearance.
- Manage the platform's engine through a PySide6 / Qt Widgets desktop interface.

Results depend on the network and engine. Kervan DPI is not a VPN or an anonymity, encryption, or IP masking service, and it cannot guarantee access on every network.

### Downloads and installation

The [v1.0.1-rc1 prerelease](https://github.com/MacallanTheRoot/kervan-dpi/releases) provides a Windows x86_64 EXE, Linux amd64 DEB, and Linux amd64 TAR.GZ. Their historical **GoodbyeDPI Turkey** filenames remain unchanged. Newer Kervan-branded application binaries have not been published.

| Platform | Published file | Use |
| --- | --- | --- |
| Windows x86_64 | GoodbyeDPI-Turkey-1.0.1rc1-windows-x86_64.exe | Download and run the EXE. |
| Debian / Kali Linux amd64 | goodbyedpi-turkey_1.0.1.rc1_amd64.deb | Install the package, then launch the app. |
| Portable Linux amd64 | GoodbyeDPI-Turkey-1.0.1rc1-linux-amd64.tar.gz | Extract the archive and run the included application. |

To install the DEB from its download directory:

~~~sh
sudo apt install ./goodbyedpi-turkey_1.0.1.rc1_amd64.deb
goodbyedpi-turkey
~~~

Install [SpoofDPI](https://github.com/xvzc/SpoofDPI) separately and make its executable available to the application. With Go installed, one supported method is:

~~~sh
go install github.com/xvzc/SpoofDPI/cmd/spoofdpi@v0.12.0
~~~

Configure the browser or application to use the HTTP proxy at 127.0.0.1:8080. See the [Linux packaging notes](docs/packaging-rc.md) for more on the published package. The release also includes SHA256SUMS for checking downloaded files.

### Architecture

The interface is built with Python, PySide6, and Qt Widgets. The Windows build uses GoodbyeDPI and WinDivert; the Linux build controls an external SpoofDPI proxy running in the user's session. These engines have different permissions and network behavior. Transparent Linux support under development is separate from the published proxy mode.

Historical installation identifiers remain for compatibility: the Linux command and package are named goodbyedpi-turkey, Linux settings use $XDG_CONFIG_HOME/goodbyedpi-turkey/config.json (or ~/.config/goodbyedpi-turkey/config.json when XDG_CONFIG_HOME is unset), and Windows settings use %APPDATA%\GoodbyeDPI-Turkey\config.json.

### Why Kervan?

When a caravan finds its road closed, it looks for another way to continue its journey. The name reflects persistence in seeking solutions to DPI-related access restrictions. **Yol Açık, Kervan Yürür.**

### Open source and contributions

Browse the [source](https://github.com/MacallanTheRoot/kervan-dpi) or share bugs and suggestions through [Issues](https://github.com/MacallanTheRoot/kervan-dpi/issues). Developed by [MacallanTheRoot](https://github.com/MacallanTheRoot).

The application code is [MIT licensed](LICENSE). GoodbyeDPI, WinDivert, and SpoofDPI are independent projects; [Zapret2](https://github.com/bol-van/zapret2), used by the Linux work in development, is another upstream project. Each has its own license. See the [third-party notices](THIRD_PARTY_NOTICES.md), [Qt/PySide6 LGPL source and relinking information](docs/qt-lgpl-compliance.md), and [website source notes](site/README.md).

Website GSAP has a separate [Standard License notice](site/vendor/gsap/NOTICE.md) and is not covered by the application's MIT license. The approved blue camel image was generated through ChatGPT for this project at the owner's request; this README does not claim it is MIT licensed.
