import SwiftUI
import UniformTypeIdentifiers

public struct SettingsView: View {
    @State private var storage = AppStorage.shared
    @State private var showingWipeAlert = false
    @State private var showingShareSheet = false
    @State private var backupData: Data?
    @State private var showingFileImporter = false
    @State private var statusMessage: String?

    public var body: some View {
        NavigationStack {
            Form {
                Section("Dữ liệu & Quyền riêng tư") {
                    VStack(alignment: .leading, spacing: 6) {
                        Label("100% Offline & Riêng tư", systemImage: "lock.shield.fill")
                            .font(.headline)
                            .foregroundColor(AppColors.primary)
                        Text("EasyMeals không có máy chủ, không thu thập dữ liệu và không kết nối Internet. Mọi thông tin về tủ lạnh và thực đơn chỉ lưu duy nhất trên thiết bị này.")
                            .font(.caption)
                            .foregroundColor(AppColors.textSecondary)
                    }
                    .padding(.vertical, 4)

                    Button {
                        exportBackup()
                    } label: {
                        Label("Sao lưu dữ liệu (Xuất JSON)", systemImage: "arrow.down.doc")
                    }

                    Button {
                        showingFileImporter = true
                    } label: {
                        Label("Phục hồi dữ liệu (Nhập JSON)", systemImage: "arrow.up.doc")
                    }
                }

                Section("Xoá dữ liệu") {
                    Button(role: .destructive) {
                        showingWipeAlert = true
                    } label: {
                        Label("Xoá toàn bộ dữ liệu trên máy", systemImage: "trash")
                            .foregroundColor(AppColors.danger)
                    }
                }

                Section("Thông tin ứng dụng") {
                    HStack {
                        Text("Phiên bản danh mục")
                        Spacer()
                        Text(storage.catalogueVersion)
                            .foregroundColor(.secondary)
                    }
                    HStack {
                        Text("Tổng công thức nấu ăn")
                        Spacer()
                        Text("\(storage.recipes.count) món")
                            .foregroundColor(.secondary)
                    }
                    HStack {
                        Text("Tổng nguyên liệu chuẩn")
                        Spacer()
                        Text("\(storage.ingredients.count) loại")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("Cài đặt")
            .alert("Xác nhận xoá dữ liệu?", isPresented: $showingWipeAlert) {
                Button("Huỷ", role: .cancel) { }
                Button("Xoá vĩnh viễn", role: .destructive) {
                    storage.wipeAllData()
                    statusMessage = "Đã xoá toàn bộ dữ liệu cá nhân."
                }
            } message: {
                Text("Hành động này sẽ làm sạch tủ lạnh, lịch sử và thực đơn. Danh mục công thức chuẩn sẽ được giữ nguyên.")
            }
            .fileImporter(isPresented: $showingFileImporter, allowedContentTypes: [.json]) { result in
                switch result {
                case .success(let url):
                    do {
                        let data = try Data(contentsOf: url)
                        try storage.importBackupData(data, replace: true)
                        statusMessage = "Nhập dữ liệu sao lưu thành công!"
                    } catch {
                        statusMessage = "Lỗi nhập file: \(error.localizedDescription)"
                    }
                case .failure(let err):
                    statusMessage = "Không thể mở file: \(err.localizedDescription)"
                }
            }
        }
    }

    private func exportBackup() {
        if let data = try? storage.exportBackupData() {
            let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent("easymeals_backup.json")
            try? data.write(to: tempURL)
            let av = UIActivityViewController(activityItems: [tempURL], applicationActivities: nil)
            if let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
               let rootVC = windowScene.windows.first?.rootViewController {
                rootVC.present(av, animated: true)
            }
        }
    }
}
