import Foundation

/// One HTTPS request to Discord's public gateway endpoint, made while the tunnel is up.
///
/// What the app can show, weakest to strongest:
/// - VPN connected / engine running: `TunnelPresentation`, not this type.
/// - `.unreachable`: no HTTP answer (reset, timeout, TLS failure).
/// - `.unexpected`: something answered, but not provably Discord: another host,
///   a redirect, a non-200 status, or a body that is not the gateway reply. Block
///   pages and captive portals land here.
/// - `.verified`: certificate-checked TLS to discord.com, no redirect, HTTP 200,
///   and the gateway JSON (`{"url": "wss://gateway.discord.gg"}`).
///
/// "Bypass verified" is deliberately not an outcome. It needs the same check to
/// fail with Kervan off on the same network (an A/B run on a real device).
struct AccessCheck: Sendable {
    enum Outcome: Sendable, Equatable { case verified, unexpected, unreachable }

    static let endpoint = URL(string: "https://discord.com/api/v10/gateway")!

    let host: String
    let outcome: Outcome
    let detail: String
    let time: Date

    static func run(url: URL = endpoint) async -> AccessCheck {
        let request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalAndRemoteCacheData, timeoutInterval: 10)
        // Ephemeral: no cookies or cache from earlier answers.
        let session = URLSession(configuration: .ephemeral, delegate: RefuseRedirects(), delegateQueue: nil)
        defer { session.finishTasksAndInvalidate() }
        do {
            let (body, response) = try await session.data(for: request)
            return evaluate(requested: url, response: response, body: body)
        } catch {
            return unreachable(requested: url, error: error)
        }
    }

    /// The whole decision, without the network, so tests can feed it block pages.
    static func evaluate(requested: URL, response: URLResponse, body: Data, now: Date = .now) -> AccessCheck {
        let host = requested.host() ?? requested.absoluteString
        func unexpected(_ why: String) -> AccessCheck {
            AccessCheck(host: host, outcome: .unexpected,
                        detail: "Unexpected answer (\(why)). Block and login pages look like this.", time: now)
        }
        guard let http = response as? HTTPURLResponse else { return unexpected("not HTTP") }
        guard let answered = http.url, answered.scheme == "https",
              let answeredHost = answered.host()?.lowercased(), answeredHost == host.lowercased()
        else { return unexpected("from another address") }
        guard http.statusCode == 200 else { return unexpected("HTTP \(http.statusCode)") }
        guard let reply = try? JSONDecoder().decode(GatewayReply.self, from: body),
              reply.url.scheme == "wss",
              let gateway = reply.url.host()?.lowercased(),
              gateway == "discord.gg" || gateway.hasSuffix(".discord.gg")
        else { return unexpected("HTTP 200, but not Discord's reply") }
        return AccessCheck(host: host, outcome: .verified,
                           detail: "Discord answered (HTTP 200). Reachability only: compare with Kervan off.",
                           time: now)
    }

    static func unreachable(requested: URL, error: Error, now: Date = .now) -> AccessCheck {
        AccessCheck(host: requested.host() ?? requested.absoluteString, outcome: .unreachable,
                    detail: "No answer: \(error.localizedDescription)", time: now)
    }

    private struct GatewayReply: Decodable {
        let url: URL
    }
}

/// A redirect is never followed: the 3xx itself is the answer, and it is not
/// Discord's reply. Captive portals and some block pages redirect.
private final class RefuseRedirects: NSObject, URLSessionTaskDelegate, Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest) async -> URLRequest? {
        nil
    }
}
