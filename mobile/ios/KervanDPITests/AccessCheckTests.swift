import Foundation
import XCTest
@testable import KervanDPI

/// Feeds AccessCheck.evaluate the answers a censored or captive network gives.
/// Only Discord's own gateway reply from discord.com over HTTPS may count.
final class AccessCheckTests: XCTestCase {
    private let endpoint = AccessCheck.endpoint
    private let gatewayJSON = Data(#"{"url": "wss://gateway.discord.gg"}"#.utf8)

    private func http(_ status: Int, at url: URL? = nil, type: String = "application/json") -> HTTPURLResponse {
        HTTPURLResponse(url: url ?? endpoint, statusCode: status, httpVersion: "HTTP/1.1",
                        headerFields: ["Content-Type": type])!
    }

    private func outcome(_ response: URLResponse, _ body: Data) -> AccessCheck.Outcome {
        AccessCheck.evaluate(requested: endpoint, response: response, body: body).outcome
    }

    // Valid

    func testGenuineGatewayReplyIsVerified() {
        XCTAssertEqual(outcome(http(200), gatewayJSON), .verified)
    }

    func testGatewayReplyWithExtraFieldsIsVerified() {
        let body = Data(#"{"url":"wss://gateway.discord.gg","shards":1}"#.utf8)
        XCTAssertEqual(outcome(http(200), body), .verified)
    }

    // Misleading

    func testBlockPageWithHTTP200IsNotVerified() {
        let page = Data("<html><body>Bu siteye erişim mahkeme kararıyla engellenmiştir.</body></html>".utf8)
        XCTAssertEqual(outcome(http(200, type: "text/html"), page), .unexpected)
    }

    func testCaptivePortalOnAnotherHostIsNotVerified() {
        let portal = URL(string: "https://login.hotspot.example/portal")!
        XCTAssertEqual(outcome(http(200, at: portal), gatewayJSON), .unexpected)
    }

    func testLookalikeHostIsNotVerified() {
        let lookalike = URL(string: "https://discord.com.attacker.example/api/v10/gateway")!
        XCTAssertEqual(outcome(http(200, at: lookalike), gatewayJSON), .unexpected)
    }

    func testPlainHTTPAnswerIsNotVerified() {
        let plain = URL(string: "http://discord.com/api/v10/gateway")!
        XCTAssertEqual(outcome(http(200, at: plain), gatewayJSON), .unexpected)
    }

    /// Redirects are refused, so the 3xx reaches evaluate as the answer.
    func testRedirectIsNotVerified() {
        for status in [301, 302, 307, 308] {
            XCTAssertEqual(outcome(http(status, type: "text/html"), Data()), .unexpected, "HTTP \(status)")
        }
    }

    func testErrorStatusesAreNotVerified() {
        for status in [204, 403, 404, 429, 451, 500, 503] {
            XCTAssertEqual(outcome(http(status), gatewayJSON), .unexpected, "HTTP \(status)")
        }
    }

    func testWrongJSONIsNotVerified() {
        let bodies = [
            #"{"url": "wss://gateway.attacker.example"}"#,
            #"{"url": "https://gateway.discord.gg"}"#,
            #"{"url": "wss://discord.gg.attacker.example"}"#,
            #"{"message": "401: Unauthorized", "code": 0}"#,
            #"{}"#,
            "",
        ]
        for body in bodies {
            XCTAssertEqual(outcome(http(200), Data(body.utf8)), .unexpected, body)
        }
    }

    func testNonHTTPResponseIsNotVerified() {
        let response = URLResponse(url: endpoint, mimeType: nil, expectedContentLength: 0, textEncodingName: nil)
        XCTAssertEqual(outcome(response, gatewayJSON), .unexpected)
    }

    func testTransportErrorIsUnreachable() {
        let reset = URLError(.networkConnectionLost)
        XCTAssertEqual(AccessCheck.unreachable(requested: endpoint, error: reset).outcome, .unreachable)
        let tls = URLError(.serverCertificateUntrusted)
        XCTAssertEqual(AccessCheck.unreachable(requested: endpoint, error: tls).outcome, .unreachable)
    }

    // Wording

    /// Even the strongest outcome claims reachability, never bypass.
    func testNoOutcomeClaimsBypass() {
        let checks = [
            AccessCheck.evaluate(requested: endpoint, response: http(200), body: gatewayJSON),
            AccessCheck.evaluate(requested: endpoint, response: http(451), body: Data()),
            AccessCheck.unreachable(requested: endpoint, error: URLError(.timedOut)),
        ]
        for check in checks {
            let text = check.detail.lowercased()
            for claim in ["bypass", "unblock", "dpi", "success", "protected", "secure"] {
                XCTAssertFalse(text.contains(claim), "\(check.outcome) says \"\(claim)\": \(text)")
            }
        }
    }
}
