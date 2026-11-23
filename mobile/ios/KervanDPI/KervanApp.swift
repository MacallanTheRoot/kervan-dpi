import SwiftUI

@main
struct KervanApp: App {
    @State private var tunnel = TunnelController()

    var body: some Scene {
        WindowGroup {
            ContentView(tunnel: tunnel)
                .task { await tunnel.observe() }
        }
    }
}
