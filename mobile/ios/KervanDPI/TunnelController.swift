import Foundation
// NetworkExtension is not Sendable-annotated; Swift 6 suggested this for
// NETunnelProviderManager crossing into the main actor (run 45228498355).
@preconcurrency import NetworkExtension
import Observation

/// Owns the app's single NETunnelProviderManager and mirrors its status.
@MainActor
@Observable
final class TunnelController {
    private(set) var status: NEVPNStatus = .invalid
    private(set) var lastError: String?
    private(set) var accessCheck: AccessCheck?
    private(set) var checking = false

    private var manager: NETunnelProviderManager?

    var isBusy: Bool {
        status == .connecting || status == .disconnecting || status == .reasserting
    }

    /// Loads the saved configuration and follows status changes for the app's lifetime.
    func observe() async {
        await load()
        // Notification is not Sendable: reduce it to Sendable values before it
        // reaches the main actor.
        let changes = NotificationCenter.default.notifications(named: .NEVPNStatusDidChange)
            .compactMap { @Sendable note -> (ObjectIdentifier, NEVPNStatus)? in
                guard let connection = note.object as? NEVPNConnection else { return nil }
                return (ObjectIdentifier(connection), connection.status)
            }
        for await (id, newStatus) in changes {
            guard let connection = manager?.connection, ObjectIdentifier(connection) == id else { continue }
            update(newStatus)
        }
    }

    func turnOn() async {
        lastError = nil
        do {
            let manager = try await preparedManager()
            try manager.connection.startVPNTunnel()
        } catch {
            lastError = error.localizedDescription
        }
    }

    func turnOff() {
        manager?.connection.stopVPNTunnel()
    }

    /// Real HTTPS request through the tunnel; shown as-is, never as bypass proof.
    func checkAccess() async {
        guard status == .connected, !checking else { return }
        checking = true
        defer { checking = false }
        let result = await AccessCheck.run(url: URL(string: "https://discord.com/")!)
        // Keep it only if the same session is still up.
        if status == .connected { accessCheck = result }
    }

    private func load() async {
        let managers = (try? await NETunnelProviderManager.loadAllFromPreferences()) ?? []
        manager = managers.first
        update(manager?.connection.status ?? .invalid)
    }

    private func update(_ newStatus: NEVPNStatus) {
        if newStatus != .connected { accessCheck = nil }
        status = newStatus
    }

    /// Creates or refreshes the on-device tunnel configuration. The first save
    /// shows the system "Add VPN Configurations" prompt.
    private func preparedManager() async throws -> NETunnelProviderManager {
        let manager = manager ?? NETunnelProviderManager()
        let proto = NETunnelProviderProtocol()
        proto.providerBundleIdentifier = TunnelIdentity.providerBundleID
        proto.serverAddress = TunnelIdentity.serverDescription
        manager.protocolConfiguration = proto
        manager.localizedDescription = "Kervan DPI"
        manager.isEnabled = true
        try await manager.saveToPreferences()
        try await manager.loadFromPreferences() // required before the first start
        self.manager = manager
        return manager
    }
}
