import NetworkExtension
import SwiftUI

/// Minimal main screen, same structure as the Android one: status, one
/// action, an access check. Branding follows the Fix04 camel and slogan.
struct ContentView: View {
    let tunnel: TunnelController

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            Image("KervanCamel")
                .resizable()
                .scaledToFit()
                .frame(maxWidth: 160)
                .saturation(tunnel.status == .connected ? 1 : 0)
                .accessibilityHidden(true)

            VStack(spacing: 8) {
                Text(headline)
                    .font(.title2.weight(.medium))
                Text(detail)
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

            if tunnel.status == .connected {
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

    private var headline: LocalizedStringKey {
        switch tunnel.status {
        case .connected: "Engine running"
        case .connecting, .reasserting: "Starting"
        case .disconnecting: "Stopping"
        default: "Off"
        }
    }

    private var detail: LocalizedStringKey {
        switch tunnel.status {
        case .connected: "Traffic passes through Kervan. Check access to confirm a site works."
        default: "Traffic goes directly to your network."
        }
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
        if tunnel.isBusy {
            ProgressView()
                .frame(height: 50)
        } else if tunnel.status == .connected {
            Button("Turn off") { tunnel.turnOff() }
                .buttonStyle(.bordered)
                .controlSize(.large)
                .frame(maxWidth: .infinity)
        } else {
            Button("Turn on") {
                Task { await tunnel.turnOn() }
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .frame(maxWidth: .infinity)
        }
    }
}
