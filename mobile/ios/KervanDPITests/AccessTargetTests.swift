import Foundation
import XCTest
@testable import KervanDPI

final class AccessTargetTests: XCTestCase {
    func testBuiltInTargetsAreDistinctHTTPSAndNotDiscord() {
        XCTAssertEqual(Set(AccessTarget.builtIn.map(\.id)).count, AccessTarget.builtIn.count)
        for target in AccessTarget.builtIn {
            XCTAssertEqual(target.url.scheme, "https", target.id)
            XCTAssertNotEqual(target.reply, .unknown, "\(target.id) has no reply check")
            XCTAssertNotEqual(target.id, AccessTarget.customID)
            XCTAssertFalse(target.url.absoluteString.contains("discord"), target.id)
        }
    }

    func testCustomAcceptsPublicHTTPS() {
        let accepted = [
            "https://example.org": "example.org",
            "example.org": "example.org",
            "  https://example.org/path?q=1  ": "example.org",
            "HTTPS://Example.ORG/": "example.org",
            "https://example.org:443/": "example.org",
        ]
        for (text, host) in accepted {
            let target = AccessTarget.custom(text)
            XCTAssertEqual(target?.host.lowercased(), host, text)
            XCTAssertEqual(target?.url.scheme?.lowercased(), "https", text)
            XCTAssertEqual(target?.reply, .unknown, text)
        }
        XCTAssertNil(AccessTarget.custom("https://example.org/#secret")?.url.fragment)
    }

    func testCustomRejectsEverythingElse() {
        let rejected = [
            "", "   ", "http://example.org", "ftp://example.org", "file:///etc/passwd", "javascript://example.org",
            "https://", "https://user:pw@example.org", "https://user@example.org", "https://example.org:8443",
            "https://192.168.1.1", "https://1.1.1.1/", "https://[::1]/", "https://localhost", "https://router",
            "https://nas.local", "https://host.internal", "https://2130706433", "https://example.org.",
            "https://-bad.org", "https://exa mple.org", "https://0x7f.0x1", String(repeating: "a", count: 3000) + ".org",
        ]
        for text in rejected {
            XCTAssertNil(AccessTarget.custom(text), text)
        }
    }
}
