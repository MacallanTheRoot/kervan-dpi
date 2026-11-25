import SwiftUI

struct DiagnosticsView: View {
    let tunnel: TunnelController

    private var diagnostics: Diagnostics {
        Diagnostics(status: TunnelPresentation(status: tunnel.status).headline,
                    target: tunnel.access.target, check: tunnel.access.result)
    }

    var body: some View {
        List(diagnostics.rows) { row in
            LabeledContent(row.name, value: row.value)
        }
        .navigationTitle("Diagnostics")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                ShareLink(item: diagnostics.text)
            }
        }
    }
}
