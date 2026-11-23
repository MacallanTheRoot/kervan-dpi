import Foundation

/// Outcome of one HTTPS request made while the tunnel is up.
struct AccessCheck: Sendable {
    let host: String
    let reachable: Bool
    let detail: String
    let time: Date

    static func run(url: URL) async -> AccessCheck {
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalAndRemoteCacheData, timeoutInterval: 10)
        request.httpMethod = "HEAD"
        let host = url.host() ?? url.absoluteString
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            let code = (response as? HTTPURLResponse)?.statusCode ?? 0
            return AccessCheck(host: host, reachable: true, detail: "HTTP \(code)", time: .now)
        } catch {
            return AccessCheck(host: host, reachable: false, detail: error.localizedDescription, time: .now)
        }
    }
}
