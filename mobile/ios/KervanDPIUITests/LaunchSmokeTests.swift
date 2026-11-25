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

    private func openSettings(_ app: XCUIApplication) {
        let gear = app.buttons["home.settings"]
        XCTAssertTrue(gear.waitForExistence(timeout: 15))
        XCTAssertEqual(gear.label, "Settings")
        gear.tap()
        XCTAssertTrue(app.navigationBars["Settings"].waitForExistence(timeout: 5))
    }

    private func element(_ id: String, in app: XCUIApplication) -> XCUIElement {
        app.descendants(matching: .any)[id].firstMatch
    }

    func testGearIsTopRightAndSettingsCloses() {
        let app = launch()
        let gear = app.buttons["home.settings"]
        XCTAssertTrue(gear.waitForExistence(timeout: 15))
        XCTAssertGreaterThan(gear.frame.midX, app.frame.width * 0.75)
        XCTAssertLessThan(gear.frame.midY, app.frame.height * 0.2)
        openSettings(app)
        XCTAssertTrue(element("check.target", in: app).exists)
        app.buttons["Done"].tap()
        XCTAssertTrue(app.staticTexts["status.headline"].waitForExistence(timeout: 5))
    }

    /// The launch argument overrides the saved target for this run only.
    func testCustomAddressMustBeHTTPS() {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["-accessCheck.target", "custom", "-accessCheck.customURL", "http://example.org"]
        app.launch()
        openSettings(app)
        XCTAssertTrue(element("check.customError", in: app).waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["check.now"].isEnabled)
    }

    func testAboutShowsIdentityVersionAndSections() {
        let app = launch()
        openSettings(app)
        element("settings.about", in: app).tap()
        XCTAssertTrue(app.navigationBars["About"].waitForExistence(timeout: 5))
        let identity = element("about.identity", in: app).label
        XCTAssertTrue(identity.contains("Kervan DPI"), identity)
        XCTAssertTrue(identity.contains("Yol Açık, Kervan Yürür."), identity)
        XCTAssertTrue(element("about.developer", in: app).label.contains("MacallanTheRoot"))
        XCTAssertTrue(element("about.repository", in: app).exists)

        for (row, title) in [("Open-source acknowledgements", "Acknowledgements"), ("Privacy", "Privacy"),
                             ("Diagnostics", "Diagnostics")] {
            let button = app.buttons[row]
            if !button.isHittable { app.swipeUp() }
            button.tap()
            XCTAssertTrue(app.navigationBars[title].waitForExistence(timeout: 5), title)
            app.navigationBars[title].buttons["About"].tap()
            XCTAssertTrue(app.navigationBars["About"].waitForExistence(timeout: 5))
        }
    }

    func testDeveloperOpensSafari() {
        let app = launch()
        openSettings(app)
        element("settings.about", in: app).tap()
        let developer = element("about.developer", in: app)
        XCTAssertTrue(developer.waitForExistence(timeout: 5))
        developer.tap()
        let safari = XCUIApplication(bundleIdentifier: "com.apple.mobilesafari")
        XCTAssertTrue(safari.wait(for: .runningForeground, timeout: 20))
        // Leave the app in front: terminating it suspended hung the next launch (run 45588697911).
        app.activate()
        XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
    }
}
