import NetworkExtension
import XCTest
@testable import KervanDPI

/// Every NEVPNStatus the system can report, including the ones a Simulator or
/// an unsigned build produce (.invalid when no configuration can be saved).
final class TunnelPresentationTests: XCTestCase {
    private let all: [NEVPNStatus] = [.invalid, .disconnected, .connecting, .connected, .reasserting, .disconnecting]

    func testOnlyConnectedShowsEngineRunning() {
        for status in all {
            let ui = TunnelPresentation(status: status)
            XCTAssertEqual(ui.engineRunning, status == .connected, "status \(status.rawValue)")
            XCTAssertEqual(ui.headline == "Engine running", status == .connected, "status \(status.rawValue)")
        }
    }

    /// Connected means the engine serves traffic, never that DPI is bypassed.
    func testNoStateClaimsBypassOrProtection() {
        let claims = ["bypass", "unblock", "dpi", "vpn active", "protected", "secure", "success"]
        for status in all {
            let ui = TunnelPresentation(status: status)
            let text = "\(ui.headline) \(ui.detail)".lowercased()
            for claim in claims {
                XCTAssertFalse(text.contains(claim), "status \(status.rawValue) says \"\(claim)\": \(text)")
            }
        }
    }

    func testActionPerStatus() {
        let expected: [NEVPNStatus: TunnelPresentation.Action] = [
            .invalid: .turnOn, .disconnected: .turnOn,
            .connecting: .busy, .reasserting: .busy, .disconnecting: .busy,
            .connected: .turnOff,
        ]
        for status in all {
            XCTAssertEqual(TunnelPresentation(status: status).action, expected[status], "status \(status.rawValue)")
        }
    }
}
