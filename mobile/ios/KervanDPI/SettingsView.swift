import SwiftUI

/// Connection Check and About.
struct SettingsView: View {
    private enum Route: Hashable { case about }

    let tunnel: TunnelController
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                ConnectionCheckSection(access: tunnel.access)
                Section {
                    NavigationLink("About", value: Route.about)
                        .accessibilityIdentifier("settings.about")
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: Route.self) { _ in
                AboutView(tunnel: tunnel)
            }
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}
