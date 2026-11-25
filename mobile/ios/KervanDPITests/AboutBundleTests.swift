import XCTest
@testable import KervanDPI

/// Runs inside the built app, so these read what it really ships.
final class AboutBundleTests: XCTestCase {
    func testBundleHasVersionAndBuild() {
        XCTAssertNotEqual(AppInfo.version(), "Unknown")
        XCTAssertNotEqual(AppInfo.build(), "Unknown")
    }

    func testAcknowledgementsAreShipped() throws {
        let text = try XCTUnwrap(AppInfo.acknowledgements)
        for part in ["ByeDPI", "hufrea", "hev-socks5-tunnel", "lwIP", "Swedish Institute of Computer Science"] {
            XCTAssertTrue(text.contains(part), part)
        }
    }
}
