import Foundation

/// The result of one HTTPS request to the selected target.
///
/// What the app can show, weakest to strongest:
/// - VPN connected / engine running: `TunnelPresentation`, not this type.
/// - `.offline`: the device has no network.
/// - `.unreachable`: no HTTP answer (reset, timeout, DNS or TLS failure).
/// - `.untrusted`: something answered with a certificate iOS does not trust.
/// - `.unexpected`: an HTTP answer that is not the target's reply: another host,
///   a redirect, another status or another body. Block pages and captive portals
///   land here.
/// - `.answered`: a custom target returned HTTP 200 over trusted TLS. Its content
///   cannot be checked.
/// - `.verified`: certificate-checked TLS, no redirect, and the reply this
///   built-in target is known to give.
///
/// "Bypass verified" is deliberately not an outcome. It needs the same check to
/// fail with Kervan off on the same network (an A/B run on a real device).
struct AccessCheck: Sendable, Equatable {
    enum Outcome: Sendable, Equatable {
        case verified, answered, unexpected, untrusted, unreachable, offline

        var isFailure: Bool { self != .verified && self != .answered }
    }

    let host: String
    let outcome: Outcome
    let detail: String
    /// Whether Kervan's engine was running for the whole request.
    let engineRunning: Bool
    let time: Date

    /// The whole decision, without the network, so tests can feed it block pages.
    static func evaluate(target: AccessTarget, response: URLResponse, body: Data,
                         engineRunning: Bool, now: Date = .now) -> AccessCheck {
        func result(_ outcome: Outcome, _ detail: String) -> AccessCheck {
            AccessCheck(host: target.host, outcome: outcome, detail: detail,
                        engineRunning: engineRunning, time: now)
        }
        func unexpected(_ why: String) -> AccessCheck {
            result(.unexpected, "Unexpected answer (\(why)). Block and login pages look like this.")
        }
        guard let http = response as? HTTPURLResponse else { return unexpected("not HTTP") }
        guard let answered = http.url, answered.scheme?.lowercased() == "https",
              answered.port == nil || answered.port == 443,
              answered.host()?.lowercased() == target.host.lowercased()
        else { return unexpected("from another address") }
        if (300..<400).contains(http.statusCode) {
            return unexpected("HTTP \(http.statusCode) redirect, not followed")
        }
        let expected = target.reply == .empty204 ? 204 : 200
        guard http.statusCode == expected else { return unexpected("HTTP \(http.statusCode)") }

        let compare = engineRunning ? "compare with Kervan off" : "compare with Kervan on"
        if target.reply == .unknown {
            return result(.answered, "Answered (HTTP 200), content not checked. Reachability only: \(compare).")
        }
        guard matches(target, body) else {
            return unexpected("HTTP \(http.statusCode), but not \(target.name)'s reply")
        }
        return result(.verified, "\(target.name) answered as expected. Reachability only: \(compare).")
    }

    static func failed(target: AccessTarget, error: Error, engineRunning: Bool, now: Date = .now) -> AccessCheck {
        let outcome: Outcome
        let detail: String
        switch (error as? URLError)?.code {
        case .notConnectedToInternet, .dataNotAllowed, .internationalRoamingOff:
            outcome = .offline
            detail = "No network connection."
        case .serverCertificateUntrusted, .serverCertificateHasBadDate,
             .serverCertificateHasUnknownRoot, .serverCertificateNotYetValid:
            outcome = .untrusted
            detail = "The certificate is not trusted, so the answer was rejected."
        default:
            outcome = .unreachable
            detail = "No answer: \(error.localizedDescription)"
        }
        return AccessCheck(host: target.host, outcome: outcome, detail: detail,
                           engineRunning: engineRunning, time: now)
    }

    private static func matches(_ target: AccessTarget, _ body: Data) -> Bool {
        switch target.reply {
        case .wikipedia:
            let info = try? JSONDecoder().decode(SiteInfo.self, from: body)
            return info?.query.general.sitename == "Wikipedia"
        case .empty204:
            return body.isEmpty
        case .cloudflareTrace:
            let lines = String(decoding: body, as: UTF8.self).split(separator: "\n")
            return lines.contains("h=\(target.host)") && lines.contains { $0.hasPrefix("colo=") }
        case .appleSuccess:
            return String(decoding: body, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
                == "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>"
        case .unknown:
            return false
        }
    }

    private struct SiteInfo: Decodable {
        struct Query: Decodable { let general: General }
        struct General: Decodable { let sitename: String }
        let query: Query
    }
}
