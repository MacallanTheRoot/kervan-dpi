import Foundation
import KervanCore

/// A non-OK status from the C engine, surfaced to iOS as the tunnel's error.
struct EngineError: LocalizedError {
    let status: kv_status_t

    var errorDescription: String? {
        "Kervan engine: " + String(cString: kv_status_string(status))
    }
}
