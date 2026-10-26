import SwiftUI

public struct RecipesView: View {
    @State private var storage = AppStorage.shared
    @State private var searchText = ""
    @State private var selectedCategory = "all"
    @State private var canCookOnly = false
    @AppStorage("easymeals.recipe.dietaryFilter") private var dietaryFilter = ""
    @AppStorage("easymeals.recipe.avoidedIngredientIds") private var avoidedIngredientIDs = ""
    @AppStorage("easymeals.recipe.preferredIngredientIds") private var preferredIngredientIDs = ""
    @AppStorage("easymeals.recipe.maxSpice") private var maxSpiceFilter = -1
    @State private var showingAvoidIngredients = false
    @State private var editingPreferencesAsLikes = false
    @State private var ingredientSelectionMode = "avoid"
    @State private var includeIngredientIDs: Set<String> = []
    @State private var excludeIngredientIDs: Set<String> = []

    private var avoidedIDs: Set<String> {
        Set(avoidedIngredientIDs.split(separator: ",").map(String.init))
    }
    private var preferredIDs: Set<String> {
        Set(preferredIngredientIDs.split(separator: ",").map(String.init))
    }

    var filteredRecipes: [Recipe] {
        storage.recipes.filter { r in
            let matchesQuery = CatalogueLoader.matches(text: r.name, query: searchText) ||
                r.ingredients.contains { CatalogueLoader.matches(text: $0.ingredientName, query: searchText) }
            let matchesCat = (selectedCategory == "all") || (r.category == selectedCategory)
            if !matchesQuery || !matchesCat { return false }
            let recipeIngredientIDs = Set(r.ingredients.map(\.ingredientId))
            if !includeIngredientIDs.isSubset(of: recipeIngredientIDs) || !excludeIngredientIDs.isDisjoint(with: recipeIngredientIDs) { return false }
            if canCookOnly {
                let (canCook, _) = EasyMealsEngine.checkRecipeStock(recipe: r, pantryLots: storage.pantryLots)
                if !canCook { return false }
            }
            if !dietaryFilter.isEmpty {
                guard r.dietaryStatus == dietaryFilter,
                      r.dietarySourceURL != nil,
                      r.dietaryVerifiedAt != nil else { return false }
            }
            if maxSpiceFilter >= 0 {
                guard let level = r.spiceLevel,
                      level <= maxSpiceFilter,
                      r.spiceSourceURL != nil,
                      r.spiceVerifiedAt != nil else { return false }
            }
            if r.ingredients.contains(where: { avoidedIDs.contains($0.ingredientId) }) { return false }
            return true
        }.sorted { first, second in
            let firstScore = first.ingredients.filter { preferredIDs.contains($0.ingredientId) }.count
            let secondScore = second.ingredients.filter { preferredIDs.contains($0.ingredientId) }.count
            return firstScore > secondScore
        }
    }

    public var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Category Filter Chips
                Picker("Chế độ ăn (đã xác minh)", selection: $dietaryFilter) {
                    Text("Mọi chế độ").tag("")
                    Text("Chay").tag("vegetarian")
                    Text("Thuần chay").tag("vegan")
                }
                .pickerStyle(.menu)
                .padding(.horizontal)
                Picker("Độ cay tối đa (đã xác minh)", selection: $maxSpiceFilter) {
                    Text("Không giới hạn").tag(-1)
                    ForEach(0...5, id: \.self) { level in Text("Mức \(level)").tag(level) }
                }
                .pickerStyle(.menu)
                .padding(.horizontal)
                Button("Nguyên liệu cần tránh (chọn thủ công) (\(avoidedIDs.count))") {
                    editingPreferencesAsLikes = false
                    ingredientSelectionMode = "avoid"
                    showingAvoidIngredients = true
                }
                .padding(.horizontal)
                Button("Nguyên liệu ưa thích (\(preferredIDs.count))") {
                    editingPreferencesAsLikes = true
                    ingredientSelectionMode = "like"
                    showingAvoidIngredients = true
                }
                .padding(.horizontal)
                HStack {
                    Button("Phải có: \(includeIngredientIDs.count)") {
                        ingredientSelectionMode = "include"
                        showingAvoidIngredients = true
                    }
                    Button("Loại nếu có: \(excludeIngredientIDs.count)") {
                        ingredientSelectionMode = "exclude"
                        showingAvoidIngredients = true
                    }
                }
                Text("Ứng dụng chỉ loại món chứa chính xác các nguyên liệu bạn chọn. Thông tin dị ứng của nguyên liệu và món chưa được xác minh, nên nguyên liệu ẩn trong sốt, bánh hay đồ chế biến có thể không bị phát hiện. Hãy luôn đọc nhãn và hỏi người nấu.")
                    .font(.footnote)
                    .foregroundColor(AppColors.textSecondary)
                    .padding(.horizontal)
                if !avoidedIDs.subtracting(storage.ingredients.map(\.id)).isEmpty {
                    Text("Một số nguyên liệu đã chọn không còn trong danh mục; sẽ được bỏ qua cho đến khi dữ liệu trở lại.")
                        .font(.footnote)
                        .foregroundColor(AppColors.textSecondary)
                        .padding(.horizontal)
                }
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        filterChip(title: "Tất cả", key: "all")
                        filterChip(title: GeneratedTokens.Labels.dish_categories["man"] ?? "Món mặn", key: "man")
                        filterChip(title: GeneratedTokens.Labels.dish_categories["rau"] ?? "Món rau", key: "rau")
                        filterChip(title: GeneratedTokens.Labels.dish_categories["canh"] ?? "Món canh", key: "canh")

                        Button {
                            canCookOnly.toggle()
                        } label: {
                            HStack(spacing: 4) {
                                Image(systemName: canCookOnly ? "checkmark.circle.fill" : "circle")
                                Text("Nấu được ngay")
                            }
                            .font(.caption.bold())
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(canCookOnly ? AppColors.primary : AppColors.secondarySurface)
                            .foregroundColor(canCookOnly ? .white : AppColors.textPrimary)
                            .cornerRadius(12)
                        }
                    }
                    .padding()
                }

                List {
                    Section { Text("\(filteredRecipes.count) công thức phù hợp").font(.footnote).foregroundColor(AppColors.textSecondary) }
                    if filteredRecipes.isEmpty {
                        Text("Không tìm thấy công thức phù hợp. Thử đổi từ khóa hoặc bộ lọc.")
                            .foregroundColor(AppColors.textSecondary)
                    } else {
                        ForEach(filteredRecipes) { recipe in
                    NavigationLink(destination: RecipeDetailView(recipe: recipe)) {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(recipe.name)
                                    .font(.headline)
                                HStack(spacing: 12) {
                                    Text("\(recipe.servings) người ăn")
                                        .font(.caption)
                                        .foregroundColor(AppColors.textSecondary)
                                    Text("\(recipe.ingredients.count) nguyên liệu")
                                        .font(.caption)
                                        .foregroundColor(AppColors.textSecondary)
                                }
                            }
                            Spacer()
                            let (canCook, _) = EasyMealsEngine.checkRecipeStock(recipe: recipe, pantryLots: storage.pantryLots)
                            if canCook {
                                Label("Đủ đồ", systemImage: "sparkles")
                                    .font(.caption2.bold())
                                    .foregroundColor(AppColors.primary)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(AppColors.primary.opacity(0.12))
                                    .cornerRadius(8)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                        }
                    }
                }
                .overlay(alignment: .top) {
                    if !dietaryFilter.isEmpty && filteredRecipes.isEmpty {
                        Text("Chưa có món nào được xác minh cho chế độ này.")
                            .font(.footnote)
                            .padding(8)
                            .background(AppColors.secondarySurface)
                    }
                }
                .searchable(text: $searchText, prompt: "Tìm tên món hoặc nguyên liệu")
            }
            .navigationTitle("Công thức")
            .sheet(isPresented: $showingAvoidIngredients) {
                NavigationStack {
                    List(storage.ingredients) { ingredient in
                        Button {
                            var updated = ingredientSelectionMode == "like" ? preferredIDs : avoidedIDs
                            if ingredientSelectionMode == "include" || ingredientSelectionMode == "exclude" {
                                var selected = ingredientSelectionMode == "include" ? includeIngredientIDs : excludeIngredientIDs
                                if selected.contains(ingredient.id) { selected.remove(ingredient.id) }
                                else { selected.insert(ingredient.id) }
                                if ingredientSelectionMode == "include" { includeIngredientIDs = selected }
                                else { excludeIngredientIDs = selected }
                                return
                            }
                            if updated.contains(ingredient.id) { updated.remove(ingredient.id) }
                            else { updated.insert(ingredient.id) }
                            if ingredientSelectionMode == "like" {
                                preferredIngredientIDs = updated.sorted().joined(separator: ",")
                            } else {
                                avoidedIngredientIDs = updated.sorted().joined(separator: ",")
                            }
                        } label: {
                            HStack {
                                Text(ingredient.name)
                                Spacer()
                                let selected = ingredientSelectionMode == "like" ? preferredIDs : ingredientSelectionMode == "include" ? includeIngredientIDs : ingredientSelectionMode == "exclude" ? excludeIngredientIDs : avoidedIDs
                                if selected.contains(ingredient.id) {
                                    Image(systemName: "checkmark").foregroundColor(AppColors.primary)
                                }
                            }
                        }
                        .foregroundColor(AppColors.textPrimary)
                    }
                    .navigationTitle(["like": "Nguyên liệu ưa thích", "include": "Công thức phải có", "exclude": "Loại món có nguyên liệu" ][ingredientSelectionMode] ?? "Nguyên liệu cần tránh")
                    .toolbar { ToolbarItem(placement: .confirmationAction) {
                        Button("Xong") { showingAvoidIngredients = false }
                    } }
                }
            }
        }
    }

    private func filterChip(title: String, key: String) -> some View {
        Button {
            selectedCategory = key
        } label: {
            Text(title)
                .font(.caption.bold())
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(selectedCategory == key ? AppColors.primary : AppColors.secondarySurface)
                .foregroundColor(selectedCategory == key ? .white : AppColors.textPrimary)
                .cornerRadius(12)
        }
    }
}

public struct RecipeDetailView: View {
    let recipe: Recipe
    @State private var servings: Int
    @State private var showingCookingMode = false
    @State private var storage = AppStorage.shared

    public init(recipe: Recipe, defaultServings: Int? = nil) {
        self.recipe = recipe
        _servings = State(initialValue: defaultServings ?? recipe.servings)
    }

    var multiplier: String {
        let mult = ExactDecimal(servings) / ExactDecimal(recipe.servings)
        return mult.description
    }

    var scaledRequirements: [AggregatedRequirement] {
        EasyMealsEngine.aggregateRequirements(recipe: recipe, multiplier: multiplier)
    }

    public var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Header & Stepper
                VStack(alignment: .leading, spacing: 8) {
                    Text(recipe.name)
                        .font(.title2.bold())

                    HStack {
                        Text("Khẩu phần:")
                            .font(.subheadline)
                        Stepper("\(servings) người", value: $servings, in: 1...20)
                            .font(.headline)
                    }
                    .padding()
                    .background(AppColors.secondarySurface)
                    .cornerRadius(12)
                }

                // Nguyên liệu
                VStack(alignment: .leading, spacing: 12) {
                    Text("Nguyên liệu")
                        .font(.title3.bold())

                    ForEach(scaledRequirements, id: \.ingredientId) { req in
                        let stock = EasyMealsEngine.getTotalIngredientStock(
                            pantryLots: storage.pantryLots,
                            ingredientId: req.ingredientId,
                            targetUnit: req.unit,
                            conversions: storage.conversions
                        )
                        let hasEnough = stock >= req.quantity
                        let isPartial = stock > .zero && stock < req.quantity

                        VStack(alignment: .leading, spacing: 2) {
                            HStack {
                                Image(systemName: hasEnough ? "checkmark.circle.fill" : "circle")
                                    .foregroundColor(hasEnough ? AppColors.primary : (isPartial ? AppColors.warning : AppColors.danger))

                                Text(req.name)
                                    .font(.body)

                                Spacer()

                                Text("\(req.quantity.description) \(req.unit)")
                                    .font(.subheadline.bold())
                                    .foregroundColor(hasEnough ? AppColors.primary : AppColors.textPrimary)
                            }
                            if hasEnough {
                                Text("✓ Có sẵn trong tủ")
                                    .font(.caption2)
                                    .foregroundColor(AppColors.primary)
                            } else if isPartial {
                                let missing = req.quantity - stock
                                Text("⚠ Có \(stock.description), thiếu \(missing.description) \(req.unit)")
                                    .font(.caption2)
                                    .foregroundColor(AppColors.warning)
                            } else {
                                Text("✗ Chưa có trong tủ")
                                    .font(.caption2)
                                    .foregroundColor(AppColors.danger)
                            }
                        }
                        .padding(.vertical, 2)
                    }
                }
                .cardStyle()

                // Hướng dẫn
                VStack(alignment: .leading, spacing: 12) {
                    Text("Các bước nấu")
                        .font(.title3.bold())
                    Text("Thời gian, độ khó và mẹo bảo quản chưa có dữ liệu được xác minh.")
                        .font(.footnote)
                        .foregroundColor(AppColors.textSecondary)

                    ForEach(Array(recipe.instructions.enumerated()), id: \.offset) { idx, step in
                        HStack(alignment: .top, spacing: 12) {
                            Text("\(idx + 1)")
                                .font(.headline)
                                .foregroundColor(AppColors.primary)
                                .frame(width: 24)
                            Text(step)
                                .font(.body)
                        }
                        .padding(.vertical, 4)
                    }
                }
                .cardStyle()

                // Nút vào chế độ nấu
                Button {
                    showingCookingMode = true
                } label: {
                    Label("Bật chế độ nấu (Giữ màn hình sáng)", systemImage: "flame.fill")
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(AppColors.primary)
                        .cornerRadius(14)
                }
            }
            .padding()
        }
        .navigationBarTitleDisplayMode(.inline)
        .fullScreenCover(isPresented: $showingCookingMode) {
            CookingModeView(recipe: recipe)
        }
    }
}

public struct CookingModeView: View {
    let recipe: Recipe
    @Environment(\.dismiss) private var dismiss
    @State private var currentStep = 0
    @State private var storage = AppStorage.shared
    @State private var servings: Int
    @State private var checkedIngredients: Set<String> = []
    @AppStorage("easymeals.recipe.keepScreenOn") private var keepScreenOn = true

    public init(recipe: Recipe) {
        self.recipe = recipe
        _servings = State(initialValue: max(1, recipe.servings))
    }

    public var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                // Thanh tiến trình
                ProgressView(value: Double(currentStep + 1), total: Double(recipe.instructions.count))
                    .tint(AppColors.primary)
                    .padding(.horizontal)

                Text("Bước \(currentStep + 1) / \(recipe.instructions.count)")
                    .font(.caption.bold())
                    .foregroundColor(AppColors.primary)

                Stepper("Khẩu phần: \(servings)", value: $servings, in: 1...20)
                    .padding(.horizontal)
                Toggle("Giữ màn hình sáng", isOn: $keepScreenOn)
                    .padding(.horizontal)
                ScrollView {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Nguyên liệu cần chuẩn bị").font(.headline)
                        ForEach(recipe.ingredients) { ingredient in
                            let quantity = (ExactDecimal(ingredient.quantity) * ExactDecimal(servings) / ExactDecimal(max(1, recipe.servings))).description
                            Toggle(isOn: Binding(
                                get: { checkedIngredients.contains(ingredient.id) },
                                set: { checked in
                                    if checked { checkedIngredients.insert(ingredient.id) }
                                    else { checkedIngredients.remove(ingredient.id) }
                                }
                            )) {
                                Text("\(ingredient.ingredientName): \(quantity) \(ingredient.unit)")
                            }
                        }
                    }
                }
                .frame(maxHeight: 160)
                Text("Thời gian, độ khó và mẹo bảo quản chưa có dữ liệu được xác minh.")
                    .font(.footnote)
                    .foregroundColor(AppColors.textSecondary)
                    .padding(.horizontal)

                Spacer()

                // Nội dung bước chữ lớn
                if currentStep < recipe.instructions.count {
                    Text(recipe.instructions[currentStep])
                        .font(.system(size: 26, weight: .medium))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)
                        .minimumScaleFactor(0.7)
                }

                Spacer()

                // Điều khiển Tiếp / Trước
                HStack(spacing: 20) {
                    Button {
                        if currentStep > 0 { currentStep -= 1 }
                    } label: {
                        Text("Trước")
                            .font(.headline)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(AppColors.secondarySurface)
                            .foregroundColor(AppColors.textPrimary)
                            .cornerRadius(12)
                    }
                    .disabled(currentStep == 0)

                    if currentStep < recipe.instructions.count - 1 {
                        Button {
                            currentStep += 1
                        } label: {
                            Text("Tiếp theo")
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(AppColors.primary)
                                .foregroundColor(.white)
                                .cornerRadius(12)
                        }
                    } else {
                        Button {
                            dismiss()
                        } label: {
                            Text("Nấu xong")
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(AppColors.primary)
                                .foregroundColor(.white)
                                .cornerRadius(12)
                        }
                    }
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 20)
            }
            .navigationTitle(recipe.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Thoát") { dismiss() }
                }
            }
            .onAppear {
                // Giữ màn hình sáng khi đang nấu
                UIApplication.shared.isIdleTimerDisabled = keepScreenOn
            }
            .onDisappear {
                // Khôi phục tắt màn hình tiết kiệm pin
                UIApplication.shared.isIdleTimerDisabled = false
            }
            .onChange(of: keepScreenOn) { _, enabled in
                UIApplication.shared.isIdleTimerDisabled = enabled
            }
        }
    }
}
