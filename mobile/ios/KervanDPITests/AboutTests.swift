import Foundation
import XCTest
@testable import KervanDPI

final class AboutTests: XCTestCase {
    func testIdentity() {
        XCTAssertEqual(AppInfo.name, "Kervan DPI")
        XCTAssertEqual(AppInfo.slogan, "Yol Açık, Kervan Yürür.")
        XCTAssertEqual(AppInfo.developer, "MacallanTheRoot")
        XCTAssertEqual(AppInfo.developerURL.absoluteString, "https://github.com/macallanTheRoot")
    }

    func testVersionComesFromTheBundleOrIsUnknown() {
        let info = ["CFBundleShortVersionString": "9.8.7", "CFBundleVersion": "42"]
        XCTAssertEqual(AppInfo.version(info), "9.8.7")
        XCTAssertEqual(AppInfo.build(info), "42")
        XCTAssertEqual(AppInfo.version([:]), "Unknown")
        XCTAssertEqual(AppInfo.build(nil), "Unknown")
    }

    func testDiagnosticsKeepCustomPathsPrivate() {
        let target = AccessTarget.custom("https://example.org/private?token=abc")!
        let check = AccessCheck.failed(target: target, error: URLError(.notConnectedToInternet), engineRunning: true)
        let text = Diagnostics(status: "Off", target: target, check: check).text
        XCTAssertTrue(text.contains("Check target: example.org"))
        XCTAssertTrue(text.contains("Kervan during check: On"))
        XCTAssertFalse(text.contains("private"))
        XCTAssertFalse(text.contains("token"))
    }

    func testDiagnosticsWithoutACheck() {
        let text = Diagnostics(status: "Off", target: nil, check: nil).text
        XCTAssertTrue(text.contains("Last check: None"))
        XCTAssertTrue(text.contains("Check target: Custom address not valid"))
    }
}
