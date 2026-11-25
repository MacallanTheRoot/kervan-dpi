import Foundation

/// The facts About shows. Versions come from the bundle, never from a constant.
enum AppInfo {
    static let name = "Kervan DPI"
    static let slogan = "Yol Açık, Kervan Yürür."
    static let developer = "MacallanTheRoot"
    static let developerURL = URL(string: "https://github.com/macallanTheRoot")!
    static let repositoryURL = URL(string: "https://github.com/MacallanTheRoot/kervan-dpi")!
    static let licenseURL = URL(string: "https://github.com/MacallanTheRoot/kervan-dpi/blob/main/LICENSE")!

    static func version(_ info: [String: Any]? = Bundle.main.infoDictionary) -> String {
        info?["CFBundleShortVersionString"] as? String ?? "Unknown"
    }

    static func build(_ info: [String: Any]? = Bundle.main.infoDictionary) -> String {
        info?["CFBundleVersion"] as? String ?? "Unknown"
    }

    static var platform: String {
        let os = ProcessInfo.processInfo.operatingSystemVersion
        return "iOS \(os.majorVersion).\(os.minorVersion).\(os.patchVersion)"
    }

    /// License texts of the engine's components, shipped in the app.
    static let acknowledgements: String? = {
        guard let url = Bundle.main.url(forResource: "Acknowledgements", withExtension: "txt") else { return nil }
        return try? String(contentsOf: url, encoding: .utf8)
    }()

    static let license = "Application code: MIT License. The camel artwork and the engine components are not covered by it."

    static let privacy = [
        "Kervan DPI has no account, analytics or advertising, and no Kervan server. The app sends nothing to its developer.",
        "Traffic is processed on this device and then goes to its destination over your own network. Kervan does not hide your IP address, encrypt your traffic or make you anonymous.",
        "While Kervan is on, DNS lookups go to Cloudflare (1.1.1.1), which applies its own privacy policy.",
        "A connection check contacts only the address you selected, and only when you start it. That site sees a normal request from your IP address. Answers are not stored.",
        "Your selected target and custom address stay on this device. The engine writes diagnostic messages to the iOS system log.",
    ]
}
