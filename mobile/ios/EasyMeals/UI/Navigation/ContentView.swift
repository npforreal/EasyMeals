import SwiftUI

public struct ContentView: View {
    @State private var storage = AppStorage.shared
    @State private var selectedTab = 0

    public init() {}

    public var body: some View {
        ZStack(alignment: .bottom) {
            TabView(selection: $selectedTab) {
                TodayView()
                    .tabItem {
                        Label("Hôm nay", systemImage: "fork.knife")
                    }
                    .tag(0)

                PantryView()
                    .tabItem {
                        Label("Tủ lạnh", systemImage: "refrigerator")
                    }
                    .tag(1)

                ShoppingView()
                    .tabItem {
                        Label("Đi chợ", systemImage: "cart")
                    }
                    .tag(2)

                RecipesView()
                    .tabItem {
                        Label("Công thức", systemImage: "book.pages")
                    }
                    .tag(3)

                SettingsView()
                    .tabItem {
                        Label("Cài đặt", systemImage: "gearshape")
                    }
                    .tag(4)
            }
            .tint(AppColors.primary)

            // Snackbar Hoàn tác toàn cục
            if let msg = storage.undoMessage {
                HStack {
                    Text(msg)
                        .font(.subheadline)
                        .foregroundColor(.white)
                    Spacer()
                    if storage.lastActionPlanId != nil {
                        Button("Hoàn tác") {
                            storage.undoLastEatMeal()
                        }
                        .font(.subheadline.bold())
                        .foregroundColor(AppColors.accent)
                    }
                }
                .padding()
                .background(Color.black.opacity(0.85))
                .cornerRadius(12)
                .padding(.horizontal)
                .padding(.bottom, 60)
                .transition(.move(edge: .bottom).combined(with: .opacity))
                .onAppear {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 4) {
                        withAnimation {
                            storage.undoMessage = nil
                        }
                    }
                }
            }
        }
    }
}
