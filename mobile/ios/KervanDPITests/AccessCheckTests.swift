import Foundation
import XCTest
@testable import KervanDPI

/// Feeds AccessCheck.evaluate the answers a censored or captive network gives.
/// Only the target's own reply, from its own host over HTTPS, may count.
final class AccessCheckTests: XCTestCase {
    private let replies: [String: (status: Int, body: String)] = [
        "wikipedia": (200, #"{"batchcomplete":"","query":{"general":{"mainpage":"Main Page","sitename":"Wikipedia"}}}"#),
        "google": (204, ""),
        "cloudflare": (200, "fl=1f1\nh=www.cloudflare.com\nip=192.0.2.1\ncolo=AMS\nhttp=http/2\n"),
        "apple": (200, "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>\n"),
    ]
    private let blockPage = "<html><body>Bu siteye erişim mahkeme kararıyla engellenmiştir.</body></html>"
    private let custom = AccessTarget.custom("https://example.org/page")!

    private func check(_ target: AccessTarget, _ status: Int, _ body: String, at url: String? = nil,
                       engineRunning: Bool = true) -> AccessCheck {
        let response = HTTPURLResponse(url: url.map { URL(string: $0)! } ?? target.url, statusCode: status,
                                       httpVersion: "HTTP/1.1", headerFields: nil)!
        return AccessCheck.evaluate(target: target, response: response, body: Data(body.utf8),
                                    engineRunning: engineRunning)
    }

    // Valid

    func testEveryBuiltInTargetAcceptsItsOwnReply() throws {
        for target in AccessTarget.builtIn {
            let reply = try XCTUnwrap(replies[target.id], target.id)
            XCTAssertEqual(check(target, reply.status, reply.body).outcome, .verified, target.id)
        }
    }

    /// HTTP 200 from a custom target is an answer, never a verified reply.
    func testCustomTargetIsAtMostAnswered() {
        XCTAssertEqual(check(custom, 200, "anything").outcome, .answered)
        XCTAssertTrue(check(custom, 200, blockPage).detail.contains("content not checked"))
    }

    // Misleading

    func testBlockPageWithHTTP200IsNotVerified() {
        for target in AccessTarget.builtIn {
            XCTAssertEqual(check(target, 200, blockPage).outcome, .unexpected, target.id)
            XCTAssertEqual(check(target, 200, "").outcome, .unexpected, target.id)
        }
    }

    func testAnotherTargetsReplyIsNotVerified() {
        for target in AccessTarget.builtIn {
            for (id, reply) in replies where id != target.id {
                XCTAssertEqual(check(target, reply.status, reply.body).outcome, .unexpected, "\(target.id) took \(id)")
            }
        }
    }

    func testAnotherAddressIsNotVerified() {
        for target in AccessTarget.builtIn + [custom] {
            let reply = replies[target.id] ?? (200, "")
            let addresses = [
                "https://login.hotspot.example/portal", "https://\(target.host).attacker.example/",
                "http://\(target.host)/", "https://\(target.host):8443/",
            ]
            for address in addresses {
                XCTAssertEqual(check(target, reply.status, reply.body, at: address).outcome, .unexpected, address)
            }
        }
    }

    /// Redirects are refused, so the 3xx reaches evaluate as the answer.
    func testRedirectIsNotVerified() {
        for target in AccessTarget.builtIn + [custom] {
            for status in [301, 302, 303, 307, 308] {
                XCTAssertEqual(check(target, status, "").outcome, .unexpected, "\(target.id) HTTP \(status)")
            }
        }
    }

    func testOtherStatusesAreNotVerified() {
        for target in AccessTarget.builtIn + [custom] {
            let reply = replies[target.id] ?? (200, "")
            for status in [200, 204, 403, 404, 429, 451, 500, 503, 511] where status != reply.status {
                XCTAssertEqual(check(target, status, reply.body).outcome, .unexpected, "\(target.id) HTTP \(status)")
            }
        }
    }

    func testNearMissBodiesAreNotVerified() {
        XCTAssertEqual(check(.wikipedia, 200, #"{"query":{"general":{"sitename":"Portal"}}}"#).outcome, .unexpected)
        XCTAssertEqual(check(.wikipedia, 200, "<title>Wikipedia</title>").outcome, .unexpected)
        XCTAssertEqual(check(.google, 204, "x").outcome, .unexpected)
        XCTAssertEqual(check(.cloudflare, 200, "h=www.cloudflare.com.attacker.example\ncolo=AMS\n").outcome, .unexpected)
        XCTAssertEqual(check(.apple, 200, "<HTML><BODY>Success</BODY></HTML>").outcome, .unexpected)
    }

    func testNonHTTPResponseIsNotVerified() {
        let response = URLResponse(url: custom.url, mimeType: nil, expectedContentLength: 0, textEncodingName: nil)
        XCTAssertEqual(AccessCheck.evaluate(target: custom, response: response, body: Data(),
                                            engineRunning: true).outcome, .unexpected)
    }

    func testTransportErrorsAreDistinguished() {
        let expected: [URLError.Code: AccessCheck.Outcome] = [
            .notConnectedToInternet: .offline,
            .timedOut: .unreachable, .networkConnectionLost: .unreachable, .cannotFindHost: .unreachable,
            .secureConnectionFailed: .unreachable,
            .serverCertificateUntrusted: .untrusted, .serverCertificateHasUnknownRoot: .untrusted,
        ]
        for (code, outcome) in expected {
            let result = AccessCheck.failed(target: custom, error: URLError(code), engineRunning: false)
            XCTAssertEqual(result.outcome, outcome, "\(code)")
            XCTAssertTrue(result.outcome.isFailure)
        }
    }

    // Wording

    /// Even the strongest outcome claims reachability, never bypass.
    func testNoOutcomeClaimsBypass() {
        var checks = [AccessCheck.failed(target: custom, error: URLError(.notConnectedToInternet), engineRunning: true),
                      AccessCheck.failed(target: custom, error: URLError(.serverCertificateUntrusted), engineRunning: true),
                      check(.wikipedia, 451, "")]
        for running in [true, false] {
            checks.append(check(custom, 200, "", engineRunning: running))
            checks.append(check(.wikipedia, 200, replies["wikipedia"]!.body, engineRunning: running))
        }
        for check in checks {
            let text = check.detail.lowercased()
            for claim in ["bypass", "unblock", "dpi", "success", "protected", "secure", "discord"] {
                XCTAssertFalse(text.contains(claim), "\(check.outcome) says \"\(claim)\": \(text)")
            }
        }
    }

    func testResultSaysWhatToCompareWith() {
        let body = replies["wikipedia"]!.body
        XCTAssertTrue(check(.wikipedia, 200, body, engineRunning: true).detail.contains("Kervan off"))
        XCTAssertTrue(check(.wikipedia, 200, body, engineRunning: false).detail.contains("Kervan on"))
    }
}
