import Foundation

/// What Settings > About > Diagnostics shows and shares. A custom target appears
/// by host only: its path may be private.
struct Diagnostics: Equatable {
    struct Row: Equatable, Identifiable {
        let name: String
        let value: String
        var id: String { name }
    }

    let rows: [Row]

    var text: String { rows.map { "\($0.name): \($0.value)" }.joined(separator: "\n") }

    init(status: String, target: AccessTarget?, check: AccessCheck?) {
        var rows = [
            Row(name: "App", value: "\(AppInfo.name) \(AppInfo.version()) (\(AppInfo.build()))"),
            Row(name: "Platform", value: AppInfo.platform),
            Row(name: "Status", value: status),
            Row(name: "Engine strategy", value: TunnelIdentity.defaultDesyncArgs),
            Row(name: "Tunnel DNS", value: TunnelIdentity.dnsServers.joined(separator: ", ")),
            Row(name: "Check target", value: target?.host ?? "Custom address not valid"),
        ]
        if let check {
            rows.append(Row(name: "Last check", value: check.detail))
            rows.append(Row(name: "Kervan during check", value: check.engineRunning ? "On" : "Off"))
            rows.append(Row(name: "Checked at", value: check.time.formatted(.iso8601)))
        } else {
            rows.append(Row(name: "Last check", value: "None"))
        }
        self.rows = rows
    }
}
