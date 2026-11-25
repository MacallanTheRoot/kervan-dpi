import Foundation

/// The network half of the connection check; `AccessCheck` judges the answer.
enum AccessProbe {
    /// More than any built-in reply needs. A longer body is cut here.
    static let maxBody = 64 * 1024

    static func run(_ target: AccessTarget, engineRunning: Bool) async -> AccessCheck {
        // Ephemeral, and nothing stored or sent from earlier answers.
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 10
        config.timeoutIntervalForResource = 15
        config.httpShouldSetCookies = false
        config.httpCookieStorage = nil
        config.urlCredentialStorage = nil
        config.urlCache = nil
        // The delegate only refuses redirects; certificate checks stay iOS's own.
        let session = URLSession(configuration: config, delegate: RefuseRedirects(), delegateQueue: nil)
        defer { session.invalidateAndCancel() }
        let request = URLRequest(url: target.url, cachePolicy: .reloadIgnoringLocalAndRemoteCacheData,
                                 timeoutInterval: 10)
        do {
            let (bytes, response) = try await session.bytes(for: request)
            var body = Data()
            for try await byte in bytes {
                body.append(byte)
                if body.count >= maxBody { break }
            }
            return AccessCheck.evaluate(target: target, response: response, body: body,
                                        engineRunning: engineRunning)
        } catch {
            return AccessCheck.failed(target: target, error: error, engineRunning: engineRunning)
        }
    }
}

/// A redirect is never followed: the 3xx itself is the answer, and it is not
/// the target's reply. Captive portals and some block pages redirect.
private final class RefuseRedirects: NSObject, URLSessionTaskDelegate, Sendable {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest) async -> URLRequest? {
        nil
    }
}
