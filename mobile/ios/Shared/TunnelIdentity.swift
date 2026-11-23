/// Identifiers and defaults shared by the app and the packet tunnel extension.
enum TunnelIdentity {
    static let appBundleID = "dev.kervan.dpi"
    static let providerBundleID = "dev.kervan.dpi.tunnel"

    /// Shown in iOS Settings > VPN. There is no remote server: the tunnel
    /// terminates on the device.
    static let serverDescription = "On-device"

    /// Same default strategy as the Android build (EngineModel.kt DesyncArgs.DEFAULT).
    static let defaultDesyncArgs = "-d1 -s1+s -r1+s"

    /// Cloudflare, the Android default DNS provider.
    static let dnsServers = ["1.1.1.1", "2606:4700:4700::1111"]

    static let tunnelIPv4 = "10.111.222.1"
    static let tunnelIPv6 = "fd6b:7672::1"
    static let mtu = 1500
}
