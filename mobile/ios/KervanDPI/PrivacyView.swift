import SwiftUI

struct PrivacyView: View {
    var body: some View {
        List(AppInfo.privacy, id: \.self) { statement in
            Text(statement)
        }
        .navigationTitle("Privacy")
        .navigationBarTitleDisplayMode(.inline)
    }
}
