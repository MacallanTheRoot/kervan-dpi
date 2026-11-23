import NetworkExtension
import os

/// Full-tunnel packet provider that terminates traffic on the device and
/// sends it out through the Kervan engine (lwIP -> ByeDPI desync). There is
/// no remote VPN server.
///
/// "Connected" in iOS means the engine reported RUNNING before start
/// returned; it does not prove that DPI bypass works.
final class PacketTunnelProvider: NEPacketTunnelProvider, @unchecked Sendable {
    private static let log = Logger(subsystem: TunnelIdentity.providerBundleID, category: "provider")

    /// The running engine; nil when stopped. Guarded because packetFlow
    /// callbacks, engine threads and stopTunnel run on different queues.
    private let engine = OSAllocatedUnfairLock<KervanEngine?>(initialState: nil)

    override func startTunnel(options: [String: NSObject]?) async throws {
        try await setTunnelNetworkSettings(Self.networkSettings())

        let newEngine = try KervanEngine(packetFlow: packetFlow) { [weak self] error in
            self?.engineFailed(error)
        }
        // Blocks until RUNNING or failure; on failure the engine has already
        // cleaned up and iOS tears the tunnel down when we throw.
        try newEngine.start(desyncArgs: TunnelIdentity.defaultDesyncArgs, mtu: TunnelIdentity.mtu)
        engine.withLock { $0 = newEngine }
        readPackets()
        Self.log.info("tunnel started")
    }

    override func stopTunnel(with reason: NEProviderStopReason) async {
        // Same Disable path as Android: stop taking packets, stop the engine
        // (joins threads, closes sockets), then let iOS remove the interface.
        let current = engine.withLock { value -> KervanEngine? in
            defer { value = nil }
            return value
        }
        current?.stop()
        Self.log.info("tunnel stopped, reason \(reason.rawValue)")
    }

    private func readPackets() {
        packetFlow.readPackets { [weak self] packets, _ in
            guard let self, let current = self.engine.withLock({ $0 }) else { return }
            for packet in packets {
                current.packetIn(packet)
            }
            self.readPackets()
        }
    }

    /// A component died while running: never leave the tunnel up with nothing
    /// behind it.
    private func engineFailed(_ error: EngineError) {
        Self.log.error("engine failed: \(error.localizedDescription, privacy: .public)")
        let current = engine.withLock { value -> KervanEngine? in
            defer { value = nil }
            return value
        }
        // nil: failed during startTunnel, which throws on its own.
        guard let current else { return }
        // Stopping from the engine's own thread would join itself; hop off it.
        DispatchQueue.global().async { [weak self] in
            current.stop()
            self?.cancelTunnelWithError(error)
        }
    }

    private static func networkSettings() -> NEPacketTunnelNetworkSettings {
        // Loopback: the tunnel ends on this device.
        let settings = NEPacketTunnelNetworkSettings(tunnelRemoteAddress: "127.0.0.1")

        let ipv4 = NEIPv4Settings(addresses: [TunnelIdentity.tunnelIPv4], subnetMasks: ["255.255.255.255"])
        ipv4.includedRoutes = [NEIPv4Route.default()]
        settings.ipv4Settings = ipv4

        let ipv6 = NEIPv6Settings(addresses: [TunnelIdentity.tunnelIPv6], networkPrefixLengths: [128])
        ipv6.includedRoutes = [NEIPv6Route.default()]
        settings.ipv6Settings = ipv6

        let dns = NEDNSSettings(servers: TunnelIdentity.dnsServers)
        dns.matchDomains = [""] // all queries; avoids the ISP's poisoned resolver
        settings.dnsSettings = dns

        settings.mtu = NSNumber(value: TunnelIdentity.mtu)
        return settings
    }
}
