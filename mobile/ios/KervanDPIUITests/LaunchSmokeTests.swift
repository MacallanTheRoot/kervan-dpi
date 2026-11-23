import XCTest

/// Runs the real app in the Simulator. No packet tunnel can run there and the
/// CI build is unsigned (no Network Extension entitlement), so the only correct
/// outcome of Turn on is a visible failure with the status still Off.
@MainActor
final class LaunchSmokeTests: XCTestCase {
    private func launch() -> XCUIApplication {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launch()
        return app
    }

    func testLaunchShowsOff() {
        let app = launch()
        let headline = app.staticTexts["status.headline"]
        XCTAssertTrue(headline.waitForExistence(timeout: 15))
        XCTAssertEqual(headline.label, "Off")
        XCTAssertTrue(app.buttons["Turn on"].isEnabled)
        XCTAssertFalse(app.buttons["Check"].exists, "access check offered while off")
        XCTAssertTrue(app.staticTexts["Yol Açık, Kervan Yürür."].exists)
    }

    func testTurnOnFailsClosedInSimulator() {
        let app = launch()
        let headline = app.staticTexts["status.headline"]
        XCTAssertTrue(headline.waitForExistence(timeout: 15))
        app.buttons["Turn on"].tap()

        XCTAssertFalse(app.staticTexts["Engine running"].waitForExistence(timeout: 10),
                       "Simulator reported a running engine")
        XCTAssertEqual(headline.label, "Off")
        XCTAssertFalse(app.buttons["Check"].exists)
        XCTAssertTrue(app.buttons["Turn on"].waitForExistence(timeout: 5))
    }
}
