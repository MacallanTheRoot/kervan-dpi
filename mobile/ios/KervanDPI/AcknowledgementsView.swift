import SwiftUI

struct AcknowledgementsView: View {
    var body: some View {
        ScrollView {
            Text(AppInfo.acknowledgements ?? "The license texts are missing from this build.")
                .font(.footnote)
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
                .accessibilityIdentifier("acknowledgements.text")
        }
        .navigationTitle("Acknowledgements")
        .navigationBarTitleDisplayMode(.inline)
    }
}
