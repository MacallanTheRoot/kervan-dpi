import Foundation
import Observation

/// The selected target and the latest check. A result belongs to one target and
/// one tunnel state; changing either drops it, including one still in flight.
@MainActor
@Observable
final class AccessCheckModel {
    enum Engine: Sendable { case running, off, changing }
    typealias Probe = @Sendable (AccessTarget, _ engineRunning: Bool) async -> AccessCheck

    private(set) var result: AccessCheck?
    private(set) var checking = false
    /// `.changing` until the saved tunnel configuration has been read.
    private(set) var engine = Engine.changing

    /// A built-in target's id, or `AccessTarget.customID`.
    var selection: String {
        didSet {
            guard selection != oldValue else { return }
            defaults.set(selection, forKey: Self.selectionKey)
            dropResult()
        }
    }

    var customText: String {
        didSet {
            guard customText != oldValue else { return }
            defaults.set(customText, forKey: Self.customKey)
            dropResult()
        }
    }

    @ObservationIgnored private var generation = 0
    @ObservationIgnored private let defaults: UserDefaults
    @ObservationIgnored private let probe: Probe

    static let selectionKey = "accessCheck.target"
    static let customKey = "accessCheck.customURL"

    init(defaults: UserDefaults = .standard, probe: @escaping Probe) {
        self.defaults = defaults
        self.probe = probe
        let known = AccessTarget.builtIn.map(\.id) + [AccessTarget.customID]
        let saved = defaults.string(forKey: Self.selectionKey) ?? ""
        selection = known.contains(saved) ? saved : AccessTarget.builtIn[0].id
        customText = defaults.string(forKey: Self.customKey) ?? ""
    }

    /// nil while the custom address is not acceptable.
    var target: AccessTarget? {
        if selection == AccessTarget.customID { return AccessTarget.custom(customText) }
        return AccessTarget.builtIn.first { $0.id == selection }
    }

    var canCheck: Bool { target != nil && !checking && engine != .changing }

    /// One real HTTPS request; shown as-is, never as bypass proof.
    func check() async {
        guard canCheck, let target else { return }
        checking = true
        defer { checking = false }
        let started = generation
        let outcome = await probe(target, engine == .running)
        // Keep it only if neither the tunnel nor the target changed meanwhile.
        if started == generation { result = outcome }
    }

    func engineChanged(to newEngine: Engine) {
        guard newEngine != engine else { return }
        engine = newEngine
        dropResult()
    }

    private func dropResult() {
        generation += 1
        result = nil
    }
}
