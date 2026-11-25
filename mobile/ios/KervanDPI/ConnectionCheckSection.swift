import SwiftUI

/// Target selection and a check that can run with Kervan on or off.
struct ConnectionCheckSection: View {
    @Bindable var access: AccessCheckModel

    var body: some View {
        Section {
            Picker("Target", selection: $access.selection) {
                ForEach(AccessTarget.builtIn) { target in
                    Text(target.name).tag(target.id)
                }
                Text("Custom address").tag(AccessTarget.customID)
            }
            .accessibilityIdentifier("check.target")

            if access.selection == AccessTarget.customID {
                TextField("https://example.org", text: $access.customText)
                    .keyboardType(.URL)
                    .textContentType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .accessibilityLabel("Custom address")
                    .accessibilityIdentifier("check.custom")
                if !access.customText.isEmpty, access.target == nil {
                    Text("Use a public https:// address, without a port, user name or IP address.")
                        .font(.footnote)
                        .foregroundStyle(.red)
                        .accessibilityIdentifier("check.customError")
                }
            }

            if let check = access.result {
                VStack(alignment: .leading) {
                    Text("\(check.host): \(check.detail)")
                        .foregroundStyle(check.outcome.isFailure ? Color.red : Color.primary)
                    Text("Kervan was \(check.engineRunning ? "on" : "off").")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }

            Button {
                Task { await access.check() }
            } label: {
                HStack {
                    Text("Check now")
                    if access.checking {
                        Spacer()
                        ProgressView()
                    }
                }
            }
            .disabled(!access.canCheck)
            .accessibilityIdentifier("check.now")
        } header: {
            Text("Connection Check")
        } footer: {
            Text("One HTTPS request to the selected site. It shows whether the site answers on this network, nothing more. To learn whether Kervan makes the difference, run it with Kervan off and on.")
        }
    }
}
