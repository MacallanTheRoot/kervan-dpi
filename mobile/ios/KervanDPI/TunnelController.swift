import Foundation
import NetworkExtension
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
        for await note in NotificationCenter.default.notifications(named: .NEVPNStatusDidChange) {
            guard let connection = note.object as? NEVPNConnection,
                  connection === manager?.connection else { continue }
            update(connection.status)
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
