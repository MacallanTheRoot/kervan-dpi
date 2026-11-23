import NetworkExtension

/// What the main screen shows for one tunnel status. Pure, so tests cover every
/// NEVPNStatus. "Engine running" is the strongest claim the app makes: it never
/// says a blocked site opens; only the access check and a real device can.
struct TunnelPresentation: Equatable {
    enum Action: Equatable { case turnOn, turnOff, busy }

    let headline: String
    let detail: String
    let engineRunning: Bool
    let action: Action

    init(status: NEVPNStatus) {
        let direct = "Traffic goes directly to your network."
        switch status {
        case .connected:
            headline = "Engine running"
            detail = "Traffic passes through Kervan. Check access to confirm a site works."
            engineRunning = true
            action = .turnOff
        case .connecting, .reasserting:
            headline = "Starting"
            detail = direct
            engineRunning = false
            action = .busy
        case .disconnecting:
            headline = "Stopping"
            detail = direct
            engineRunning = false
            action = .busy
        default:
            headline = "Off"
            detail = direct
            engineRunning = false
            action = .turnOn
        }
    }
}
