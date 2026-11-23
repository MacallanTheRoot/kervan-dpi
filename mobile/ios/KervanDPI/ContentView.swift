import SwiftUI

/// Minimal main screen, same structure as the Android one: status, one
/// action, an access check. Branding follows the Fix04 camel and slogan.
struct ContentView: View {
    let tunnel: TunnelController

    private var ui: TunnelPresentation { TunnelPresentation(status: tunnel.status) }

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            Image("KervanCamel")
                .resizable()
                .scaledToFit()
                .frame(maxWidth: 160)
                .saturation(ui.engineRunning ? 1 : 0)
                .accessibilityHidden(true)

            VStack(spacing: 8) {
                Text(ui.headline)
                    .font(.title2.weight(.medium))
                    .accessibilityIdentifier("status.headline")
                Text(ui.detail)
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                if let error = tunnel.lastError {
                    Text(error)
                        .font(.footnote)
                        .foregroundStyle(.red)
                        .multilineTextAlignment(.center)
                }
            }

            if ui.engineRunning {
                accessRow
            }
            Spacer()

            primaryAction
            Text("Yol Açık, Kervan Yürür.")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .padding(24)
    }

    @ViewBuilder
    private var accessRow: some View {
        HStack {
            if let check = tunnel.accessCheck {
                Text("\(check.host): \(check.detail)")
                    .foregroundStyle(check.reachable ? Color.primary : Color.red)
            } else {
                Text("Access not checked")
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button("Check") {
                Task { await tunnel.checkAccess() }
            }
            .disabled(tunnel.checking)
        }
        .font(.callout)
    }

    @ViewBuilder
    private var primaryAction: some View {
        switch ui.action {
        case .busy:
            ProgressView()
                .frame(height: 50)
        case .turnOff:
            Button("Turn off") { tunnel.turnOff() }
                .buttonStyle(.bordered)
                .controlSize(.large)
                .frame(maxWidth: .infinity)
        case .turnOn:
            Button("Turn on") {
                Task { await tunnel.turnOn() }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .frame(maxWidth: .infinity)
        }
    }
}
