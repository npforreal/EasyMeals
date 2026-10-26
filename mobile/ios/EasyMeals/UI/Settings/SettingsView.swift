import SwiftUI
import UniformTypeIdentifiers

public struct SettingsView: View {
    @State private var storage = AppStorage.shared
    @ObservedObject private var theme = ThemeManager.shared
    @State private var showingWipeAlert = false
    @State private var showingShareSheet = false
    @State private var backupData: Data?
    @State private var showingFileImporter = false
    @State private var statusMessage: String?
    @AppStorage("allow_leftovers") private var allowLeftovers: Bool = true
    @AppStorage("leftover_days") private var leftoverDays: Int = PlanLimits.leftoverDefaultDays

    // C1 - Vòng 13: cài đặt hộ gia đình cục bộ (lưu vào tệp trạng thái, có backup/restore).
    @State private var hhSize: Int = AppStorage.shared.householdSize
    @State private var hhServings: Int = AppStorage.shared.defaultServings
    @State private var hhPeriods: Set<String> = Set(AppStorage.shared.mealPeriods)
    @State private var hhSkipDates: String = AppStorage.shared.skipDates.joined(separator: ", ")

    public var body: some View {
        NavigationStack {
            Form {
                Section("Giao diện & Màu sắc") {
                    Picker("Chế độ hiển thị", selection: $theme.themeMode) {
                        Text("Theo hệ thống").tag("system")
                        Text("Sáng").tag("light")
                        Text("Tối").tag("dark")
                    }
                    .pickerStyle(.segmented)

                    Picker("Bảng màu nhấn", selection: $theme.palette) {
                        Text("Xanh lá").tag("green")
                        Text("Cam đất").tag("terracotta")
                        Text("Xanh biển").tag("ocean")
                        Text("Tím mận").tag("plum")
                        Text("Hồng đào").tag("peach")
                    }
                }

                // Section: Đồ ăn dư (A1 - Vòng 13)
                Section("Đồ ăn dư") {
                    Toggle("Cho dùng lại đồ ăn dư", isOn: $allowLeftovers)
                    if allowLeftovers {
                        Picker("Dùng lại trong tối đa", selection: $leftoverDays) {
                            ForEach(PlanLimits.leftoverMinDays...PlanLimits.leftoverMaxDays, id: \.self) { d in
                                Text("\(d) ngày").tag(d)
                            }
                        }
                        Text("Bật để thực đơn tận dụng phần dư của mẻ nấu trước, tránh lãng phí thực phẩm. Mỗi phần dư chỉ được dùng lại một lần.")
                            .font(.caption)
                            .foregroundColor(AppColors.textSecondary)
                    }
                }

                // Section: Hộ gia đình (C1 - Vòng 13)
                Section("Hộ gia đình") {
                    Stepper("Số người ăn cùng: \(hhSize)", value: $hhSize, in: 1...20, step: 1)
                        .onChange(of: hhSize) { newSize in
                            AppStorage.shared.setHouseholdSize(newSize)
                        }
                    Stepper("Khẩu phần mặc định mỗi người: \(hhServings)", value: $hhServings, in: 1...50, step: 1)
                        .onChange(of: newServings) { AppStorage.shared.setDefaultServings(newServings) }
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Bữa cần lập mỗi ngày")
                            .font(.subheadline)
                            .fontWeight(.semibold)
                        HStack(spacing: 8) {
                            ForEach(["breakfast", "lunch", "dinner"], id: \.self) { period in
                                let label = ["breakfast": "Sáng", "lunch": "Trưa", "dinner": "Tối"][period, default: period]
                                Toggle(label, isOn: Binding(
                                    get: { hhPeriods.contains(period) },
                                    set: { isOn in
                                        if isOn { hhPeriods.insert(period) } else { hhPeriods.remove(period) }
                                        AppStorage.shared.setMealPeriods(Array(hhPeriods.sorted()))
                                    }
                                ))
                                .toggleStyle(.button)
                            }
                        }
                        if hhPeriods.isEmpty {
                            Text("Mặc định: Trưa + Tối")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }
                    }
                    TextField("Ngày không nấu / ăn ngoài (YYYY-MM-DD, cách nhau bằng dấu phẩy)", text: $hhSkipDates)
                        .textFieldStyle(.roundedBorder)
                        .keyboardType(.numbersAndPunctuation)
                        .onChange(of: hhSkipDates) { newText in
                            let dates = newText.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
                            AppStorage.shared.setSkipDates(Array(dates))
                        }
                    Text("Ngày không nấu sẽ bị bỏ qua khi lập thực đơn, không ảnh hưởng lịch sử kho.")
                        .font(.caption)
                        .foregroundColor(AppColors.textSecondary)
                }

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
