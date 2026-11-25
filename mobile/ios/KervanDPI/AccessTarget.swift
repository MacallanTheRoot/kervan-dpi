import Foundation

/// One address the connection check can ask, and how to recognise its real reply.
struct AccessTarget: Sendable, Equatable, Identifiable {
    enum Reply: Sendable, Equatable {
        /// Wikipedia site info: JSON naming the site.
        case wikipedia
        /// HTTP 204 with an empty body.
        case empty204
        /// Cloudflare trace: text lines, one of them `h=<host>`.
        case cloudflareTrace
        /// Apple's connectivity test page, byte for byte.
        case appleSuccess
        /// A custom address: the app cannot know what the real page looks like.
        case unknown
    }

    static let customID = "custom"

    let id: String
    let name: String
    let url: URL
    let reply: Reply

    var host: String { url.host() ?? url.absoluteString }

    static let wikipedia = AccessTarget(
        id: "wikipedia", name: "Wikipedia",
        url: URL(string: "https://en.wikipedia.org/w/api.php?action=query&meta=siteinfo&siprop=general&format=json")!,
        reply: .wikipedia)
    static let google = AccessTarget(
        id: "google", name: "Google",
        url: URL(string: "https://www.gstatic.com/generate_204")!, reply: .empty204)
    static let cloudflare = AccessTarget(
        id: "cloudflare", name: "Cloudflare",
        url: URL(string: "https://www.cloudflare.com/cdn-cgi/trace")!, reply: .cloudflareTrace)
    static let apple = AccessTarget(
        id: "apple", name: "Apple",
        url: URL(string: "https://www.apple.com/library/test/success.html")!, reply: .appleSuccess)

    /// The first one is the default.
    static let builtIn = [wikipedia, google, cloudflare, apple]

    /// A custom target, or nil unless the text is a plain public HTTPS address:
    /// no other scheme, no credentials, no other port, no IP address and no
    /// local name. A missing scheme means https.
    static func custom(_ text: String) -> AccessTarget? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, trimmed.count <= 2048 else { return nil }
        let full = trimmed.contains("://") ? trimmed : "https://" + trimmed
        guard var parts = URLComponents(string: full),
              parts.scheme?.lowercased() == "https",
              parts.user == nil, parts.password == nil,
              parts.port == nil || parts.port == 443,
              let host = parts.encodedHost?.lowercased(), isPublicName(host)
        else { return nil }
        parts.fragment = nil
        guard let url = parts.url else { return nil }
        return AccessTarget(id: customID, name: "Custom address", url: url, reply: .unknown)
    }

    private static func isPublicName(_ host: String) -> Bool {
        let labels = host.split(separator: ".", omittingEmptySubsequences: false)
        guard host.count <= 253, labels.count >= 2, let last = labels.last else { return false }
        let allowed = Set("abcdefghijklmnopqrstuvwxyz0123456789-")
        for label in labels {
            guard (1...63).contains(label.count), label.allSatisfy(allowed.contains),
                  !label.hasPrefix("-"), !label.hasSuffix("-") else { return false }
        }
        // A last label that starts with a digit is an IPv4 address, not a name.
        guard last.first?.isNumber == false else { return false }
        return !["local", "localhost", "internal", "lan", "home", "arpa"].contains(String(last))
    }
}
