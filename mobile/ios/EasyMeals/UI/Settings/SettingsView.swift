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
    @SwiftUI.AppStorage("allow_leftovers") private var allowLeftovers: Bool = true
    @SwiftUI.AppStorage("leftover_days") private var leftoverDays: Int = PlanLimits.leftoverDefaultDays
    // F2 - Vòng 13: nhắc việc cục bộ (UserDefaults, không lưu lên server).
    @SwiftUI.AppStorage("reminders_enabled") private var remindersEnabled: Bool = false
    @State private var reminderStatus: String?

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

                // Section: Nhắc việc (F2 - Vòng 13)
                Section("Nhắc việc") {
                    Toggle("Nhắc hạn dùng & bữa ăn hôm nay", isOn: Binding(
                        get: { remindersEnabled },
                        set: { newValue in
                            Task { await updateReminders(newValue) }
                        }
                    ))
                    Text("Nhắc lúc 9:00 sáng theo múi giờ của máy về lô sắp hết hạn và bữa ăn trong ngày. Thông báo được tạo trên máy, không gửi dữ liệu đi; ứng dụng chỉ xin quyền thông báo khi bạn bật.")
                        .font(.caption)
                        .foregroundColor(AppColors.textSecondary)
                    if let reminderStatus {
                        Text(reminderStatus)
                            .font(.caption)
                            .foregroundColor(reminderStatus.hasPrefix("Đã bật") ? AppColors.primary : AppColors.danger)
                    }
                }

                // Section: Hộ gia đình (C1 - Vòng 13)
                Section("Hộ gia đình") {
                    Stepper("Số người ăn cùng: \(hhSize)", value: $hhSize, in: 1...20, step: 1)
                        .onChange(of: hhSize) { newSize in
                            AppStorage.shared.setHouseholdSize(newSize)
                        }
                    Stepper("Khẩu phần mặc định mỗi người: \(hhServings)", value: $hhServings, in: 1...50, step: 1)
                        .onChange(of: hhServings) { newServings in
                            AppStorage.shared.setDefaultServings(newServings)
                        }
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

                // Section: Lịch sử & thống kê (F1 - Vòng 13)
                Section("Lịch sử & thống kê (30 ngày)") {
                    let history = storage.historySummary()
                    HStack(spacing: 16) {
                        historyStat("Bữa đã nấu", "\(history.cooked.inWindow)")
                        historyStat("Tổng bữa", "\(history.cooked.total)")
                        historyStat("Đồ dư dùng lại", "\(history.leftovers.reusedDishesInWindow)")
                    }
                    Text(
                        "Chi tiêu đã nhập: " + (history.spending.lotsWithPrice > 0
                            ? "\(formatVnd(history.spending.inWindow)) (30 ngày)"
                            : "chưa có dữ liệu giá")
                    )
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    if history.spending.lotsMissingPrice > 0 {
                        Text("Chỉ tính \(history.spending.lotsWithPrice) lô có nhập giá; \(history.spending.lotsMissingPrice) lô chưa có giá.")
                            .font(.caption)
                            .foregroundColor(AppColors.textSecondary)
                    }
                    Text("Biến động kho: \(history.stock.inWindow) lần trong 30 ngày (\(history.stock.consumedCount) trừ, \(history.stock.restoredCount) cộng); tổng \(history.stock.totalMovements) bản ghi.")
                        .font(.caption)
                        .foregroundColor(AppColors.textSecondary)

                    if history.cooked.meals.isEmpty {
                        Text("Chưa có bữa ăn nào được đánh dấu “Đã ăn”.")
                            .font(.caption)
                            .foregroundColor(AppColors.textSecondary)
                    } else {
                        ForEach(history.cooked.meals.prefix(5)) { meal in
                            Text("• \(formatDay(meal.plannedFor)) · \(periodLabel(meal.mealPeriod)): \(meal.dishNames.joined(separator: ", "))\(meal.leftoverReuseCount > 0 ? " (+\(meal.leftoverReuseCount) đồ dư)" : "")")
                                .font(.caption)
                        }
                        if !history.cooked.topRecipes.isEmpty {
                            Text("Nấu nhiều nhất: " + history.cooked.topRecipes.map { "\($0.name) ×\($0.count)" }.joined(separator: " · "))
                                .font(.caption2)
                                .foregroundColor(AppColors.textSecondary)
                        }
                    }

                    if history.waste.expiredLotCount > 0 {
                        Text("\(history.waste.expiredLotCount) lô đã quá hạn mà vẫn còn trong tủ: " +
                             history.waste.expiredLots.prefix(5).map {
                                 "\($0.ingredientName.isEmpty ? $0.ingredientId : $0.ingredientName) (\($0.remainingQuantity) \($0.unit))"
                             }.joined(separator: ", "))
                            .font(.caption)
                            .foregroundColor(AppColors.danger)
                    }
                    Text("Ứng dụng chưa ghi nhận lãng phí; mục quá hạn chỉ là đồ còn trong tủ, không phải số liệu lãng phí đã xác nhận.")
                        .font(.caption2)
                        .foregroundColor(AppColors.textSecondary)
                }

                Section("Dữ liệu & Quyền riêng tư") {
                    VStack(alignment: .leading, spacing: 6) {
                        Label("100% Offline & Riêng tư", systemImage: "lock.shield.fill")
                            .font(.headline)
                            .foregroundColor(AppColors.primary)
                        Text("EasyMeals không có máy chủ, không thu thập dữ liệu và không kết nối Internet. Mọi thông tin về tủ lạnh và thực đơn chỉ lưu duy nhất trên thiết bị này. Ứng dụng chỉ xin quyền thông báo khi bạn bật nhắc việc.")
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

                    Text("Định dạng sao lưu: schema \(BackupManager.schemaVersion) · đọc được file schema 1–\(BackupManager.schemaVersion) và bản sao lưu của bản Web.")
                        .font(.caption2)
                        .foregroundColor(AppColors.textSecondary)

                    if let statusMessage {
                        Text(statusMessage)
                            .font(.caption)
                            .foregroundColor(statusMessage.hasPrefix("Lỗi") || statusMessage.hasPrefix("Không") ? AppColors.danger : AppColors.primary)
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
            .onAppear {
                // F2: làm mới nội dung nhắc theo dữ liệu mới nhất mỗi lần mở Cài đặt.
                if remindersEnabled {
                    NotificationScheduler.refresh(storage: storage)
                }
            }
        }
    }

    @MainActor
    private func updateReminders(_ enabled: Bool) async {
        if !enabled {
            remindersEnabled = false
            NotificationScheduler.disable()
            reminderStatus = "Đã tắt nhắc việc."
            return
        }

        let granted = await NotificationScheduler.requestAuthorization()
        guard granted else {
            remindersEnabled = false
            NotificationScheduler.disable()
            reminderStatus = "Chưa được cấp quyền thông báo. Mở Cài đặt hệ thống › EasyMeals › Thông báo để bật."
            return
        }
        remindersEnabled = true
        NotificationScheduler.refresh(storage: storage)
        reminderStatus = "Đã bật nhắc việc lúc 9:00 sáng (giờ máy)."
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

@ViewBuilder
private func historyStat(_ label: String, _ value: String) -> some View {
    VStack(alignment: .leading, spacing: 2) {
        Text(value)
            .font(.title3.bold())
            .foregroundColor(AppColors.primary)
        Text(label)
            .font(.caption2)
            .foregroundColor(AppColors.textSecondary)
    }
}

private func formatVnd(_ value: Int) -> String {
    let formatter = NumberFormatter()
    formatter.numberStyle = .decimal
    formatter.groupingSeparator = "."
    formatter.locale = Locale(identifier: "vi_VN")
    let text = formatter.string(from: NSNumber(value: value)) ?? "\(value)"
    return "\(text) đ"
}

private func formatDay(_ value: String) -> String {
    guard value.count >= 10 else { return value }
    let parts = value.prefix(10).split(separator: "-")
    guard parts.count == 3 else { return value }
    return "\(parts[2])/\(parts[1])/\(parts[0])"
}

private func periodLabel(_ value: String) -> String {
    switch value {
    case "breakfast": return "Sáng"
    case "lunch": return "Trưa"
    case "dinner": return "Tối"
    default: return value
    }
}
