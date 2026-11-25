import SwiftUI

struct AboutView: View {
    private enum Route: Hashable { case acknowledgements, privacy, diagnostics }

    let tunnel: TunnelController

    var body: some View {
        Form {
            Section {
                VStack {
                    Image("KervanCamel")
                        .resizable()
                        .scaledToFit()
                        .frame(maxWidth: 96)
                        .accessibilityHidden(true)
                    Text(AppInfo.name)
                        .font(.title2)
                    Text(AppInfo.slogan)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .accessibilityElement(children: .combine)
                .accessibilityIdentifier("about.identity")
            }

            Section {
                Link(destination: AppInfo.developerURL) {
                    LabeledContent("Developer", value: AppInfo.developer)
                }
                .accessibilityIdentifier("about.developer")
                .accessibilityHint("Opens in your browser")
                Link("Project repository", destination: AppInfo.repositoryURL)
                    .accessibilityIdentifier("about.repository")
                    .accessibilityHint("Opens in your browser")
            }

            Section {
                LabeledContent("Version", value: AppInfo.version())
                LabeledContent("Build", value: AppInfo.build())
                LabeledContent("Platform", value: AppInfo.platform)
            }

            Section {
                Link("License", destination: AppInfo.licenseURL)
                    .accessibilityIdentifier("about.license")
                    .accessibilityHint("Opens in your browser")
                NavigationLink("Open-source acknowledgements", value: Route.acknowledgements)
                NavigationLink("Privacy", value: Route.privacy)
                NavigationLink("Diagnostics", value: Route.diagnostics)
            } footer: {
                Text(AppInfo.license)
            }
        }
        .navigationTitle("About")
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(for: Route.self) { route in
            switch route {
            case .acknowledgements: AcknowledgementsView()
            case .privacy: PrivacyView()
            case .diagnostics: DiagnosticsView(tunnel: tunnel)
            }
        }
    }
}
