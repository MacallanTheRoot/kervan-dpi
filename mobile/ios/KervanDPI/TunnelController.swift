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
    let access = AccessCheckModel(probe: { await AccessProbe.run($0, engineRunning: $1) })

    private var manager: NETunnelProviderManager?

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

    private func load() async {
        let managers = (try? await NETunnelProviderManager.loadAllFromPreferences()) ?? []
        manager = managers.first
        update(manager?.connection.status ?? .invalid)
    }

    private func update(_ newStatus: NEVPNStatus) {
        status = newStatus
        switch newStatus {
        case .connected: access.engineChanged(to: .running)
        case .connecting, .reasserting, .disconnecting: access.engineChanged(to: .changing)
        default: access.engineChanged(to: .off)
        }
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
