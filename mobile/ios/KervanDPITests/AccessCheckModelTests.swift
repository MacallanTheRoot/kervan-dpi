import Foundation
import XCTest
@testable import KervanDPI

@MainActor
final class AccessCheckModelTests: XCTestCase {
    /// A probe the test releases by hand, to change state mid-request.
    private actor Gate {
        private var waiting: CheckedContinuation<Void, Never>?
        private var opened = false
        func wait() async {
            if opened { return }
            await withCheckedContinuation { waiting = $0 }
        }
        func open() {
            opened = true
            waiting?.resume()
        }
    }

    private func freshDefaults() -> UserDefaults {
        let suite = "AccessCheckModelTests-\(UUID().uuidString)"
        addTeardownBlock { UserDefaults.standard.removePersistentDomain(forName: suite) }
        return UserDefaults(suiteName: suite)!
    }

    private nonisolated static func answer(_ target: AccessTarget, _ running: Bool) -> AccessCheck {
        AccessCheck(host: target.host, outcome: .verified, detail: "", engineRunning: running, time: .now)
    }

    private func model(_ defaults: UserDefaults? = nil, gate: Gate? = nil) -> AccessCheckModel {
        AccessCheckModel(defaults: defaults ?? freshDefaults()) { target, running in
            await gate?.wait()
            return Self.answer(target, running)
        }
    }

    func testDefaultIsTheFirstBuiltInTarget() async {
        XCTAssertEqual(model().target, AccessTarget.builtIn[0])
    }

    func testUnknownSavedTargetFallsBack() async {
        let defaults = freshDefaults()
        defaults.set("discord", forKey: AccessCheckModel.selectionKey)
        XCTAssertEqual(model(defaults).target, AccessTarget.builtIn[0])
    }

    func testSelectionAndCustomAddressPersist() async {
        let defaults = freshDefaults()
        let first = model(defaults)
        first.selection = AccessTarget.customID
        first.customText = "https://example.org"
        let second = model(defaults)
        XCTAssertEqual(second.selection, AccessTarget.customID)
        XCTAssertEqual(second.target?.host, "example.org")
    }

    func testNoCheckWithInvalidCustomAddress() async {
        let model = model()
        model.engineChanged(to: .running)
        model.selection = AccessTarget.customID
        model.customText = "http://example.org"
        XCTAssertFalse(model.canCheck)
        await model.check()
        XCTAssertNil(model.result)
    }

    func testNoCheckWhileTunnelChangesOrIsUnknown() async {
        let model = model()
        XCTAssertFalse(model.canCheck, "state not read yet")
        model.engineChanged(to: .off)
        XCTAssertTrue(model.canCheck)
        model.engineChanged(to: .changing)
        XCTAssertFalse(model.canCheck)
    }

    func testResultRecordsWhetherKervanWasRunning() async {
        let model = model()
        model.engineChanged(to: .off)
        await model.check()
        XCTAssertEqual(model.result?.engineRunning, false)
        model.engineChanged(to: .running)
        XCTAssertNil(model.result, "result of another tunnel state kept")
        await model.check()
        XCTAssertEqual(model.result?.engineRunning, true)
    }

    func testChangingTargetDropsResult() async {
        let model = model()
        model.engineChanged(to: .running)
        await model.check()
        XCTAssertNotNil(model.result)
        model.selection = "google"
        XCTAssertNil(model.result)
    }

    func testTunnelRestartDuringCheckDropsResult() async {
        await expectDropped { model in
            model.engineChanged(to: .changing)
            model.engineChanged(to: .running)
        }
    }

    func testTargetChangeDuringCheckDropsResult() async {
        await expectDropped { $0.selection = "google" }
    }

    private func expectDropped(_ change: (AccessCheckModel) -> Void) async {
        let gate = Gate()
        let model = model(gate: gate)
        model.engineChanged(to: .running)
        let check = Task { await model.check() }
        while !model.checking { await Task.yield() }
        XCTAssertFalse(model.canCheck, "second check offered while one runs")
        change(model)
        await gate.open()
        await check.value
        XCTAssertNil(model.result)
        XCTAssertFalse(model.checking)
    }
}
