import Foundation
import KervanCore
import NetworkExtension
import os

/// Swift owner of the C engine in packet mode. The extension process holds at
/// most one (the C core enforces a single instance).
///
/// The C callbacks run on engine threads. Everything they read is immutable
/// after init, and `kv_engine_stop` joins those threads before returning, so
/// no callback can outlive `stop()` or `deinit`.
final class KervanEngine: @unchecked Sendable {
    private static let log = Logger(subsystem: TunnelIdentity.providerBundleID, category: "engine")

    private let handle: OpaquePointer
    private let packetFlow: NEPacketTunnelFlow
    private let onFailure: @Sendable (EngineError) -> Void

    /// - Parameter onFailure: called from an engine thread when a component
    ///   dies while running. The provider must cancel the tunnel (fail closed).
    init(packetFlow: NEPacketTunnelFlow, onFailure: @escaping @Sendable (EngineError) -> Void) throws {
        var created: OpaquePointer?
        let status = kv_engine_create(&created)
        guard status == KV_OK, let created else { throw EngineError(status: status) }
        handle = created
        self.packetFlow = packetFlow
        self.onFailure = onFailure
    }

    deinit {
        kv_engine_destroy(handle) // stops first if still running
    }

    /// Blocks until the engine is serving or has failed and cleaned up.
    func start(desyncArgs: String, mtu: Int) throws {
        var lastStatus = KV_ERR_PROXY_START
        // The loopback port is random; retry a taken port a few times.
        for _ in 0..<3 {
            lastStatus = startOnce(desyncArgs: desyncArgs, mtu: mtu, port: UInt16.random(in: 20000...60000))
            if lastStatus == KV_OK { return }
            if lastStatus != KV_ERR_PROXY_START { break }
        }
        throw EngineError(status: lastStatus)
    }

    /// Idempotent; blocks until engine threads are joined and sockets closed.
    func stop() {
        kv_engine_stop(handle)
    }

    var isRunning: Bool {
        kv_engine_state(handle) == KV_STATE_RUNNING
    }

    /// One packet read from `packetFlow`. Drops (and reports) instead of blocking.
    @discardableResult
    func packetIn(_ packet: Data) -> kv_status_t {
        packet.withUnsafeBytes { raw in
            kv_engine_packet_in(handle, raw.baseAddress, raw.count)
        }
    }

    private func startOnce(desyncArgs: String, mtu: Int, port: UInt16) -> kv_status_t {
        var config = kv_engine_config_t()
        config.struct_size = UInt32(MemoryLayout<kv_engine_config_t>.size)
        config.tun_fd = Int32(KV_TUN_PACKET_MODE)
        config.tun_mtu = UInt32(mtu)
        config.socks_port = port
        config.enable_udp = 1
        // Sockets opened by the provider do not enter its own tunnel, so there
        // is no protect step on iOS. Verify on device (README test plan).
        config.require_protect = 0
        config.protect_cb = nil
        config.runtime_dir = nil
        config.user = Unmanaged.passUnretained(self).toOpaque()
        config.log_cb = { user, level, message in
            guard let message else { return }
            let text = String(cString: message)
            switch level {
            case KV_LOG_ERROR: KervanEngine.log.error("\(text, privacy: .public)")
            case KV_LOG_WARN: KervanEngine.log.warning("\(text, privacy: .public)")
            default: KervanEngine.log.info("\(text, privacy: .public)")
            }
        }
        config.state_cb = { user, state, reason in
            guard let user, state == KV_STATE_FAILED else { return }
            let engine = Unmanaged<KervanEngine>.fromOpaque(user).takeUnretainedValue()
            engine.onFailure(EngineError(status: reason))
        }
        config.packet_out_cb = { user, packet, length, family in
            guard let user, let packet else { return }
            let engine = Unmanaged<KervanEngine>.fromOpaque(user).takeUnretainedValue()
            let proto = NSNumber(value: family == 6 ? AF_INET6 : AF_INET)
            engine.packetFlow.writePackets([Data(bytes: packet, count: length)], withProtocols: [proto])
        }
        return desyncArgs.withCString { args in
            config.desync_args = args // copied by the core
            return kv_engine_start(handle, &config)
        }
    }
}
