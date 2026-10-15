# Kervan DPI — Türkçe rehber

[English README](../README.md) · **Yol Açık, Kervan Yürür.**

![Kervan DPI mavi deve simgesi](../assets/kervan-camel.png)

Kervan DPI, DPI kaynaklı erişim kısıtlamalarında kullanılan motorları yönetmek için açık kaynaklı bir masaüstü arayüzüdür. Windows'ta paketli GoodbyeDPI ve WinDivert'i, Linux'ta kullanıcı tarafından ayrıca kurulan SpoofDPI yerel HTTP proxy'sini yönetir. Önceki proje adı **GoodbyeDPI Turkey** idi; depo adresi ve bazı ayar yolları uyumluluk için korunur.

> **Sürüm durumu:** Kervan DPI markalı `1.0.1rc2` Windows EXE'si henüz yayımlanmadı. Önceki fix01 kaynağı Windows 11'de derlendi ve kısmen test edildi; buradaki değişmiş kaynak yeniden yerel derleme ve tam QA gerektirir. [Hazırlık durumu](release/kervan-dpi-readiness.md).

## Platformlar

| Platform | İşlev | Durum |
| --- | --- | --- |
| Windows 11 x64 | Paketli GoodbyeDPI ve WinDivert | Fix01 markalı EXE kısmen gerçek cihazda doğrulandı; değişen aday için yeni derleme ve tam yerel QA gerekiyor. |
| Diğer Windows sürümleri | Windows kaynak ve derleme yolu | Bu aday için yerel doğrulama yok. |
| Debian/Kali Linux amd64 | Ayrı kurulan SpoofDPI yerel HTTP proxy'si | Geliştirme aşaması; istemci proxy'yi ayrıca seçmeli. |
| Linux şeffaf `nfqws2`/NFQUEUE | Deneysel entegrasyon | Yayımlanmadı; sistem geneli şeffaf çalışma doğrulanmadı. |
| Android / iOS | Gelecek planı | İndirilebilir uygulama yok. |

## Özellikler ve Windows kullanımı

Arayüzde DNS seçimi, **Enable/Disable**, durum ve etkinlik günlüğü, sistem tepsisi, açık/koyu tema ve isteğe bağlı otomatik başlatma bulunur. Linux SpoofDPI için **Normal** ve `-window-size 4` ekleyen **Compatibility** proxy modları vardır; sonuç ağa bağlıdır.

Tercihler üst başlıktaki düğmeden açılır. **Otomatik Güncellemeler** seçeneği, imzalı yükleme ve yerel Windows QA tamamlanana kadar **Kapalı** ve kullanılamaz durumdadır. **Güncellemeleri Denetle** bağımsız çalışır ve yalnızca resmi kararlı sürümleri gösterir. [Elle güncelleme ve imzalama durumu](release/windows-update.md).

Markalı Windows dosyası **henüz indirilemez**. Doğrulanmış sürüm yayımlandığında EXE veya taşınabilir ZIP'i yalnızca projenin [GitHub Releases](https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/releases) sayfasından ve aynı sürüme ait SHA-256 bildirimiyle edinin. Eski sürüm dosyaları önceki adı taşır. PowerShell'de `Get-FileHash .\Kervan-DPI.exe -Algorithm SHA256` çıktısını bildirimle karşılaştırın. Şu anda Kervan DPI kurucusu veya kod imzalı EXE yoktur.

Taşınabilir ZIP'i denetiminizdeki bir klasöre açıp `Kervan-DPI.exe` dosyasını çalıştırın. WinDivert için Windows UAC yönetici izni isteyebilir. DNS sağlayıcısını seçin ve **Enable** düğmesine basın. İşiniz bitince **Disable** ile motoru durdurun. Pencerenin X düğmesi tepsiye gizler; tepsideki **Show Kervan DPI** pencereyi açar, **Quit Kervan DPI** etkin motoru durdurup uygulamadan çıkar. Son markalı EXE'nin bu davranışı Windows'ta yeniden test edilmelidir.

Ayarlar `%APPDATA%\GoodbyeDPI-Turkey\config.json` dosyasında kalır. Yeni otomatik başlatma kısayolu `Kervan DPI.lnk` adını alır; mevcut `GoodbyeDPI-Turkey GUI.lnk` korunur. Yükseltirken hedefi inceleyin. Marka değişimi için otomatik ayar yolu taşıma veya silme yapılmaz; boş bir profilde paketli eski `config.json`, mevcut dosyanın üzerine yazılmadan içe alınabilir. [Geçiş ve geri dönüş rehberi](release/windows-migration.md).

## Güvenlik, Linux ve sorun giderme

Kervan DPI bir VPN, anonimleştirme aracı veya şifreli tünel değildir; her ağda erişim garantisi vermez. Windows'ta yönetici izni ve paket sürücüsü kullanılır. Eski WinDivert hizmetini veya motor klasörünü sahipliğini incelemeden silmeyin. [Onaylı deve görselinin kaynağı](branding/kervan-camel-source.md) kayıtlıdır; yeniden dağıtım hakkı yayın öncesinde doğrulanmalıdır.

Linux'ta SpoofDPI ayrıca kurulmalıdır. **Enable**, `127.0.0.1:8080` üzerinde yalnızca yerel HTTP proxy açar; tarayıcı veya uygulama bu proxy'yi seçmelidir. Sistem proxy, rota veya güvenlik duvarı değiştirilmez. Şeffaf NFQUEUE modu kullanıma hazır değildir. [Linux geliştirme ve yerel proxy rehberi](linux-development.md) ile [Nightshift doğrulaması](engineering/phase-7h-nightshift-final-report.md) ayrıntıları içerir.

- **UAC reddedildi / Enable başarısız:** UAC istemini, yetkileri ve etkinlik günlüğünü inceleyin. Sonucu [Windows QA listesine](release/windows-qa-checklist.md) kaydedin.
- **Bağlantı hâlâ engelli:** **Disable**, ardından **Quit Kervan DPI** seçin; normal HTTPS erişimini tekrar deneyin. DNS seçimini ve diğer proxy/filtreleri kontrol edin. Tekrarlanabilir sorunu [GitHub Issues](https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/issues) üzerinden bildirin.
- **Pencere kayboldu:** Sistem tepsisinden açın veya tepsiden tamamen çıkın.
- **Ayarlar/otomatik başlatma farklı:** Yukarıdaki config dosyasını ve mevcut kısayolun hedefini inceleyin; yükseltme testinden önce yedek alın.
- **Linux proxy çalışmıyor:** SpoofDPI kurulumunu, `127.0.0.1:8080` dinleyicisini ve istemci proxy ayarını kontrol edin.

## Kaynaktan derleme, katkı ve lisans

Windows derlemesini gerçek Windows makinesinde **Python 3.13 x64**, `py` başlatıcısı ve depodaki onaylı deve görseliyle, `.venv` içermeyen yeni bir kaynak dizininde yapın:

```bat
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-windows-rc.txt
build.bat
```

Çıktı `dist\Kervan-DPI.exe` olmalıdır. [Tam Windows derleme yönergesi](release/windows-build.md) ve [Linux geliştirme rehberi](linux-development.md) ayrı belgelerde. Kaynak test komutu: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -q`.

Katkı veya hata bildirimi için [issue açın](https://github.com/MacallanTheRoot/GoodbyeDPI-Turkey-GUI/issues); işletim sistemi/sürümü, uygulama sürümü, tekrar adımları, beklenen/gerçek sonucu ve kişisel bilgileri temizlenmiş günlükleri ekleyin. Motor veya ağ yaşam döngüsü değişikliklerinde ilgili platformun yerel testi gerekir.

Uygulama kodu ve **eski proje kalkan simgesi** deponun [MIT lisansı](../LICENSE) kapsamındadır. Yeni deve görselinin dağıtım hakları henüz kesinleşmedi. Paketli bileşenlerin ayrı lisansları için [üçüncü taraf bildirimlerine](../THIRD_PARTY_NOTICES.md), `bin/licenses/`, `packaging/licenses/` ve [Qt/PySide6 kaynak ve yeniden derleme belgesine](qt-lgpl-compliance.md) bakın. Qt belgesi önceki RC1'i anlatır; bu adayın karşılık gelen kaynakları yayın öncesinde yeniden doğrulanmalıdır.

Kervan DPI uygulaması [MacallanTheRoot](https://github.com/MacallanTheRoot) tarafından geliştirilmektedir. Uygulama üst verisindeki telif satırı `Copyright (c) 2026 MacallanTheRoot` biçimindedir; bu satır kod imzası kimliği değildir. Windows entegrasyonu [GoodbyeDPI Turkey](https://github.com/cagritaskn/goodbyedpi-turkey), asıl [GoodbyeDPI](https://github.com/ValdikSS/GoodbyeDPI) ve [WinDivert](https://github.com/basil00/WinDivert) çalışmalarına dayanır. Linux proxy'si ayrı kurulan [SpoofDPI](https://github.com/xvzc/SpoofDPI) ile çalışır; deneysel şeffaf çalışma [Zapret2](https://github.com/bol-van/zapret2) teknolojisini inceler. Bu projeler bağımsızdır.
