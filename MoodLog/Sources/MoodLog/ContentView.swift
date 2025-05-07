//
//  ContentView.swift
//  MoodLog
//
//  Created by abel on 2025/3/28.
//

import SwiftUI
import Foundation
import CoreData
#if canImport(UIKit)
import UIKit
#endif
import StoreKit

// 定义支持的语言
enum AppLanguage: Int, CaseIterable, Identifiable {
    case chinese = 0
    case english = 1
    case japanese = 2

    var id: Int { self.rawValue }

    var name: String {
        switch self {
        case .chinese:
            return "中文"
        case .english:
            return "English"
        case .japanese:
            return "日本語"
        }
    }

    var code: String {
        switch self {
        case .chinese:
            return "zh-Hans"
        case .english:
            return "en"
        case .japanese:
            return "ja"
        }
    }

    static func fromCode(_ code: String) -> AppLanguage {
        switch code {
        case "zh-Hans": return .chinese
        case "en": return .english
        case "ja": return .japanese
        default: return .chinese
        }
    }
}

// 定义外观模式
enum AppearanceMode: Int, CaseIterable, Identifiable {
    case system = 0
    case light = 1
    case dark = 2

    var id: Int { self.rawValue }

    var name: String {
        return String.getLocalizedAppearanceName(for: self.rawValue)
    }

    var displayName: String {
        return String.getLocalizedAppearanceDisplayName(for: self.rawValue)
    }

    var iconName: String {
        switch self {
        case .system:
            return "iphone"
        case .light:
            return "sun.max.fill"
        case .dark:
            return "moon.fill"
        }
    }
}

// 应用状态类，管理整个应用的状态
internal class AppState: ObservableObject {
    // 是否已解锁（使用Face ID/Touch ID验证后）
    @Published var isUnlocked: Bool = true

    // 当前选中的日期
    @Published var selectedDate: Date = Date()

    // 当前活动tab
    @Published var activeTab: Int = 0

    // 当前选择的语言
    @Published var selectedLanguage: AppLanguage = {
        // 从用户默认设置中获取语言设置
        let languageCode = LocalizationHelper.shared.getCurrentLanguage()
        return AppLanguage.fromCode(languageCode)
    }()

    // 当前选择的外观模式
    @Published var selectedAppearance: AppearanceMode = {
        let savedValue = UserDefaults.standard.integer(forKey: "selectedAppearance")
        return AppearanceMode(rawValue: savedValue) ?? .system
    }()

    // 切换语言
    func switchLanguage(to language: AppLanguage) {
        // 更新选中的语言
        selectedLanguage = language

        // 使用LocalizationHelper更新系统语言设置
        LocalizationHelper.shared.setLanguage(language.code)

        // 保存到用户设置
        UserDefaults.standard.set(language.rawValue, forKey: "selectedLanguage")

        // 强制刷新本地化资源
        LocalizationHelper.shared.reloadLocalizationBundle()

        // 输出调试信息
        print("语言已切换为：\(language.name)(\(language.code))")
    }

    // 切换外观模式
    func switchAppearance(to mode: AppearanceMode) {
        self.selectedAppearance = mode

        // 保存设置
        UserDefaults.standard.set(mode.rawValue, forKey: "selectedAppearance")

        // 应用外观设置
        applyAppearanceSettings()
    }

    // 应用外观模式
    private func applyAppearanceSettings() {
        #if canImport(UIKit)
        DispatchQueue.main.async {
            let scenes = UIApplication.shared.connectedScenes
            let windowScene = scenes.first as? UIWindowScene
            let window = windowScene?.windows.first

            switch self.selectedAppearance {
            case .light:
                window?.overrideUserInterfaceStyle = .light
            case .dark:
                window?.overrideUserInterfaceStyle = .dark
            case .system:
                window?.overrideUserInterfaceStyle = .unspecified
            }
        }
        #endif
    }

    // 用户是否订阅了Pro版本
    @Published var isPro: Bool = UserDefaults.standard.bool(forKey: "isPro")

    // 更新Pro状态
    func updateProStatus() {
        isPro = UserDefaults.standard.bool(forKey: "isPro")
    }
}

// 活动视图
struct ActivityView: View {
    @State private var selectedMonth: Date = Date()
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var journalStore: JournalEntryStore
    @State private var showMonthPicker = false
    @State private var forceRefresh: Bool = false

    // 星期几标题
    private let weekDays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map { $0.localized }

    var body: some View {
        NavigationView {
            ScrollView {
                // 月份标题
                HStack {
                    Button(action: {
                        showMonthPicker = true
                    }) {
                        HStack {
                            Text(monthString(from: selectedMonth))
                                .font(.custom("Times New Roman", size: 36))
                                .italic()
                                .foregroundColor(Color(red: 0.2, green: 0.2, blue: 0.2))

                            Image(systemName: "chevron.down")
                                .font(.headline)
                                .foregroundColor(Color(red: 0.2, green: 0.2, blue: 0.2))
                        }
                        .padding(.leading)
                    }
                    .sheet(isPresented: $showMonthPicker) {
                        MonthPickerView(selectedMonth: $selectedMonth, showMonthPicker: $showMonthPicker)
                    }

                    Spacer()
                }
                .padding(.top)

                Divider()
                    .padding(.horizontal)

                // 日历网格
                VStack(spacing: 10) {
                    // 星期几标题
                    HStack(spacing: 0) {
                        ForEach(weekDays, id: \.self) { day in
                            Text(day)
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .foregroundColor(Color(red: 0.3, green: 0.3, blue: 0.3))
                        }
                    }
                    .padding(.bottom, 5)

                    // 日期网格
                    LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 0), count: 7), spacing: 10) {
                        ForEach(getDaysInMonth(), id: \.self) { date in
                            if date.isWithinMonth(selectedMonth) {
                                // 日期单元格
                                Button(action: {
                                    appState.selectedDate = date
                                    appState.activeTab = 0  // 切换到时间线视图查看详情
                                }) {
                                    VStack(spacing: 2) {
                                        Text("\(date.day)")
                                            .font(.system(size: 16, weight: .medium))
                                            .foregroundColor(Color(red: 0.3, green: 0.3, blue: 0.3))

                                        // 如果有心情记录，显示对应的圆点
                                        if hasMoodEntry(for: date) {
                                            Circle()
                                                .fill(getMoodColor(for: date))
                                                .frame(width: 8, height: 8)
                                        }
                                    }
                                    .frame(height: 45)
                                    .frame(maxWidth: .infinity)
                                    .background(
                                        RoundedRectangle(cornerRadius: 12)
                                            .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                                    )
                                }
                                .buttonStyle(PlainButtonStyle())
                            } else {
                                // 其他月份的日期显示为空白
                                Rectangle()
                                    .fill(Color.clear)
                                    .frame(height: 45)
                            }
                        }
                    }
                }
                .padding(.horizontal)

                Spacer()

                // 月份统计
                VStack(spacing: 15) {
                    Text("Monthly Mood Statistics".localized)
                        .font(.headline)
                        .foregroundColor(Color(red: 0.3, green: 0.3, blue: 0.3))

                    HStack(spacing: 20) {
                        // 修复ForEach语法，直接使用键值对数组
                        let moodStatsArray = getMoodStats().map { (key: $0.key, count: $0.value) }.sorted(by: { $0.key > $1.key })
                        ForEach(moodStatsArray, id: \.key) { stats in
                            VStack(spacing: 5) {
                                Text("\(stats.count)")
                                    .font(.title2)
                                    .fontWeight(.bold)
                                    .foregroundColor(Color(red: 0.2, green: 0.2, blue: 0.2))

                                Text(getMoodName(for: stats.key))
                                    .font(.caption)
                                    .foregroundColor(Color(red: 0.4, green: 0.4, blue: 0.4))

                                Circle()
                                    .fill(getMoodColorByValue(value: stats.key))
                                    .frame(width: 12, height: 12)
                            }
                        }
                    }
                    .padding()
                    .background(Color(UIColor.secondarySystemBackground))
                    .cornerRadius(15)
                }
                .padding()

                // 底部月份导航
                HStack {
                    Button(action: {
                        // 上个月
                        withAnimation {
                            selectedMonth = Calendar.current.date(byAdding: .month, value: -1, to: selectedMonth)!
                        }
                    }) {
                        Image(systemName: "chevron.left")
                            .font(.headline)
                            .padding()
                            .foregroundColor(Color(red: 0.2, green: 0.2, blue: 0.2))
                    }

                    Spacer()

                    Button(action: {
                        // 回到今天
                        withAnimation {
                            selectedMonth = Date()
                        }
                    }) {
                        Text("Today".localized)
                            .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            .font(.headline)
                    }

                    Spacer()

                    Button(action: {
                        // 下个月
                        withAnimation {
                            selectedMonth = Calendar.current.date(byAdding: .month, value: 1, to: selectedMonth)!
                        }
                    }) {
                        Image(systemName: "chevron.right")
                            .font(.headline)
                            .padding()
                            .foregroundColor(Color(red: 0.2, green: 0.2, blue: 0.2))
                    }
                }
                .padding(.horizontal)
                .padding(.bottom, 10)
            }
            .navigationTitle("Monthly Overview".localized)
            .navigationBarTitleDisplayMode(.inline)
            .id(forceRefresh) // 使用id强制视图刷新
            .onLanguageChange {
                // 语言变化时刷新视图
                forceRefresh.toggle()
            }
        }
    }

    // 从月份计算该月的所有日期
    func getDaysInMonth() -> [Date] {
        let calendar = Calendar.current

        // 找到当前月的第一天
        let components = calendar.dateComponents([.year, .month], from: selectedMonth)
        let startOfMonth = calendar.date(from: components)!

        // 找到当前月的第一天是周几
        let firstWeekday = calendar.component(.weekday, from: startOfMonth)

        // 找到当前月的总天数
        let daysInMonth = calendar.range(of: .day, in: .month, for: selectedMonth)!.count

        // 生成日期数组，包括前一个月和后一个月的日期以填充整个网格
        var dates: [Date] = []

        // 添加上个月的日期
        let daysToAddBefore = firstWeekday - 1
        if daysToAddBefore > 0 {
            for i in (1...daysToAddBefore).reversed() {
                if let date = calendar.date(byAdding: .day, value: -i, to: startOfMonth) {
                    dates.append(date)
                }
            }
        }

        // 添加当前月的日期
        for i in 0..<daysInMonth {
            if let date = calendar.date(byAdding: .day, value: i, to: startOfMonth) {
                dates.append(date)
            }
        }

        // 添加下个月的日期填充到42个日期（6周）
        let remainingDays = 42 - dates.count
        for i in 0..<remainingDays {
            if let date = calendar.date(byAdding: .day, value: daysInMonth + i, to: startOfMonth) {
                dates.append(date)
            }
        }

        return dates
    }

    // 检查日期是否有心情记录
    func hasMoodEntry(for date: Date) -> Bool {
        return !journalStore.entriesForDate(date).isEmpty
    }

    // 获取日期的心情颜色
    func getMoodColor(for date: Date) -> Color {
        let entries = journalStore.entriesForDate(date)
        guard !entries.isEmpty else {
            return .clear
        }

        // 使用第一个条目的心情颜色
        return getMoodColorByValue(value: entries.first!.mood)
    }

    // 根据心情值获取颜色
    func getMoodColorByValue(value: Int) -> Color {
        switch value {
        case 0:
            return .indigo  // 糟糕
        case 1:
            return .blue    // 不好
        case 2:
            return .green   // 一般
        case 3:
            return .orange  // 不错
        case 4:
            return .yellow  // 超棒
        default:
            return .gray
        }
    }

    // 根据心情值获取名称
    func getMoodName(for value: Int) -> String {
        switch value {
        case 0: return "Awful".localized
        case 1: return "Bad".localized
        case 2: return "Okay".localized
        case 3: return "Good".localized
        case 4: return "Awesome".localized
        default: return "Unknown".localized
        }
    }

    // 获取该月的心情统计
    func getMoodStats() -> [Int: Int] {
        return journalStore.getMoodValues(for: selectedMonth)
    }

    // 月份字符串
    func monthString(from date: Date) -> String {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "yyyy年M月"
        return dateFormatter.string(from: date)
    }
}

// 扩展Date以获取日期的日
extension Date {
    var day: Int {
        return Calendar.current.component(.day, from: self)
    }

    func isWithinMonth(_ date: Date) -> Bool {
        let calendar = Calendar.current
        let components1 = calendar.dateComponents([.year, .month], from: self)
        let components2 = calendar.dateComponents([.year, .month], from: date)
        return components1.year == components2.year && components1.month == components2.month
    }
}

// 主视图
struct ContentView: View {
    @EnvironmentObject var appState: AppState
    @EnvironmentObject var journalStore: JournalEntryStore
    @State private var selectedTab = 0
    @State private var showingNewEntrySheet = false
    @State private var showingDatePicker = false
    @State private var weekDates: [Date] = []
    @State private var forceRefresh = false
    
    var body: some View {
        TabView(selection: $selectedTab) {
            NavigationView {
                TimelineView()
            }
            .tabItem {
                Image(systemName: "calendar")
                Text("Timeline".localized)
            }
            .tag(0)
            
            NavigationView {
                ActivityView()
            }
            .tabItem {
                Image(systemName: "chart.bar")
                Text("Activity".localized)
            }
            .tag(1)
            
            NavigationView {
                ReportView()
            }
            .tabItem {
                Image(systemName: "doc.text.chart")
                Text("Report".localized)
            }
            .tag(2)
            
            NavigationView {
                SettingsView()
            }
            .tabItem {
                Image(systemName: "gear")
                Text("Settings".localized)
            }
            .tag(3)
        }
        .onAppear {
            updateWeekDates()
        }
    }
    
    // MARK: - Helper Methods
    
    func updateWeekDates() {
        let calendar = Calendar.current

        // 查找当前周的星期日
        let sunday = calendar.date(from: calendar.dateComponents([.yearForWeekOfYear, .weekOfYear], from: appState.selectedDate))!

        // 生成一周的日期
        weekDates = (0..<7).map { calendar.date(byAdding: .day, value: $0, to: sunday)! }
    }

    // 将Date格式化为星期几
    func dayOfWeek(from date: Date) -> String {
        let dateFormatter = DateFormatter()
        dateFormatter.dateFormat = "E" // 简短的星期几表示
        // 设置日期格式器使用当前语言
        dateFormatter.locale = Locale(identifier: LocalizationHelper.shared.currentLanguage)
        return dateFormatter.string(from: date)
    }

    // 将Date格式化为YYYY年MM月DD日 星期几
    func dateString(from date: Date) -> String {
        let dateFormatter = DateFormatter()
        // 根据当前语言选择不同的日期格式
        if LocalizationHelper.shared.currentLanguage.starts(with: "zh") {
            dateFormatter.dateFormat = "yyyy年MM月dd日 EEEE"
        } else if LocalizationHelper.shared.currentLanguage.starts(with: "ja") {
            dateFormatter.dateFormat = "yyyy年MM月dd日 EEEE"
        } else {
            dateFormatter.dateFormat = "MMMM dd, yyyy EEEE"
        }
        // 设置日期格式器使用当前语言
        dateFormatter.locale = Locale(identifier: LocalizationHelper.shared.currentLanguage)
        return dateFormatter.string(from: date)
    }

    // 从Date获取月份字符串，格式为YYYY年M月
    func monthString(from date: Date) -> String {
        let dateFormatter = DateFormatter()
        // 根据当前语言选择不同的月份格式
        if LocalizationHelper.shared.currentLanguage.starts(with: "zh") {
            dateFormatter.dateFormat = "yyyy年M月"
        } else if LocalizationHelper.shared.currentLanguage.starts(with: "ja") {
            dateFormatter.dateFormat = "yyyy年M月"
        } else {
            dateFormatter.dateFormat = "MMMM yyyy"
        }
        // 设置日期格式器使用当前语言
        dateFormatter.locale = Locale(identifier: LocalizationHelper.shared.currentLanguage)
        return dateFormatter.string(from: date)
    }

    // 显示选中日期的日记条目
    var entriesForSelectedDate: some View {
        // 强制每次视图更新时重新查询
        @State var entries = journalStore.entriesForDate(appState.selectedDate)

        return Group {
            if entries.isEmpty {
                VStack(spacing: 20) {
                    Spacer()
                    Image(systemName: "note.text")
                        .font(.largeTitle)
                        .foregroundColor(.gray)
                    Text("No entries for this day".localized)
                        .font(.headline)
                        .foregroundColor(.gray)
                    Text("Selected date".localized + ": \(dateString(from: appState.selectedDate))")
                        .font(.caption)
                        .foregroundColor(.gray)
                        .padding(.bottom, 4)
                    Button(action: {
                        showAddEntry = true
                    }) {
                        Text("Add your first entry".localized)
                            .font(.headline)
                            .foregroundColor(.white)
                            .padding()
                            .background(Color(red: 0.15, green: 0.35, blue: 0.3))
                            .cornerRadius(10)
                    }
                    Spacer()
                }
                .padding()
            } else {
                ScrollView {
                    Text("Entry count".localized + ": \(entries.count)")
                        .font(.caption)
                        .foregroundColor(.gray)
                        .frame(maxWidth: .infinity, alignment: .trailing)
                        .padding(.trailing)

                    LazyVStack(spacing: 15) {
                        ForEach(entries) { entry in
                            JournalEntryCard(entry: entry)
                                .padding(.horizontal)
                        }
                    }
                    .padding(.vertical)
                }
            }
        }
        .onAppear {
            // 每次视图出现时刷新
            entries = journalStore.entriesForDate(appState.selectedDate)
        }
        .onChange(of: appState.selectedDate) { _, _ in
            // 日期变化时刷新
            entries = journalStore.entriesForDate(appState.selectedDate)
        }
        .onChange(of: journalStore.entries.count) { _, _ in
            // 记录数量变化时刷新
            entries = journalStore.entriesForDate(appState.selectedDate)
        }
    }
}

// 更新DatePickerView使用本地化字符串
struct DatePickerView: View {
    @Environment(\.presentationMode) var presentationMode
    @EnvironmentObject var appState: AppState
    @State private var tempDate = Date()

    var body: some View {
        NavigationView {
            VStack {
                DatePicker(
                    "Select a date".localized,
                    selection: $tempDate,
                    displayedComponents: [.date]
                )
                .datePickerStyle(GraphicalDatePickerStyle())
                .padding()

                HStack(spacing: 20) {
                    Button(action: {
                        tempDate = Date()
                    }) {
                        Text("Today".localized)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(UIColor.tertiarySystemBackground))
                            .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            .cornerRadius(10)
                    }

                    Button(action: {
                        appState.selectedDate = tempDate
                        presentationMode.wrappedValue.dismiss()
                    }) {
                        Text("Confirm".localized)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(red: 0.15, green: 0.35, blue: 0.3))
                            .foregroundColor(.white)
                            .cornerRadius(10)
                    }
                }
                .padding()
            }
            .navigationTitle("Choose Date".localized)
            .navigationBarItems(leading: Button(action: {
                presentationMode.wrappedValue.dismiss()
            }) {
                Text("Cancel".localized)
            })
            .onAppear {
                tempDate = appState.selectedDate
            }
            .onChange(of: tempDate) { _, newValue in
                print("Selected date: \(newValue)")
            }
        }
    }
}

#if os(iOS)
struct ImagePicker: UIViewControllerRepresentable {
    @Binding var selectedImage: UIImage?
    @Environment(\.presentationMode) private var presentationMode
    
    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config = PHPickerConfiguration()
        config.filter = .images
        let picker = PHPickerViewController(configuration: config)
        picker.delegate = context.coordinator
        return picker
    }
    
    func updateUIViewController(_ uiViewController: PHPickerViewController, context: Context) {}
    
    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }
    
    class Coordinator: NSObject, PHPickerViewControllerDelegate {
        let parent: ImagePicker
        
        init(_ parent: ImagePicker) {
            self.parent = parent
        }
        
        func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
            parent.presentationMode.wrappedValue.dismiss()
            
            guard let provider = results.first?.itemProvider else { return }
            
            if provider.canLoadObject(ofClass: UIImage.self) {
                provider.loadObject(ofClass: UIImage.self) { image, _ in
                    DispatchQueue.main.async {
                        self.parent.selectedImage = image as? UIImage
                    }
                }
            }
        }
    }
}
#endif

#if os(iOS)
struct JournalEntryItem: Identifiable {
    let id: UUID
    let mood: Int
    let moodType: MoodType
    let content: String
    let date: Date
    let image: UIImage?
}
#else
struct JournalEntryItem: Identifiable {
    let id: UUID
    let mood: Int
    let moodType: MoodType
    let content: String
    let date: Date
}
#endif

// 设置视图
struct SettingsView: View {
    @AppStorage("isReminderEnabled") private var isReminderEnabled = false
    @AppStorage("isLockEntriesEnabled") private var isLockEntriesEnabled = false
    @State private var showingProView = false
    @State private var showLanguageSelector = false
    @State private var showAppearanceSelector = false
    @State private var forceRefresh: Bool = false
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationView {
            List {
                // Pro版本区域
                Section {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Text("MoodLog Pro".localized)
                                .font(.title)
                                .fontWeight(.bold)
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))

                            if appState.isPro {
                                Image(systemName: "checkmark.seal.fill")
                                    .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                                    .font(.title2)
                            }
                        }

                        if appState.isPro {
                            Text("Pro features are active".localized)
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        } else {
                            Text("Unlock premium features".localized)
                                .font(.subheadline)
                                .foregroundColor(.secondary)

                            Button(action: {
                                showingProView = true
                            }) {
                                Text("Subscribe Now".localized)
                                    .font(.headline)
                                    .foregroundColor(.white)
                                    .padding(.vertical, 8)
                                    .padding(.horizontal, 16)
                                    .background(Color(red: 0.15, green: 0.35, blue: 0.3))
                                    .cornerRadius(8)
                            }
                            .padding(.top, 5)
                        }
                    }
                    .padding(.vertical, 8)
                }
                .listRowBackground(Color(UIColor.secondarySystemBackground))

                // 通用设置
                Section(header: Text("General".localized)) {
                    Button(action: {
                        showLanguageSelector = true
                    }) {
                        HStack {
                            Image(systemName: "globe")
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))

                            Text("Language".localized)

                            Spacer()

                            Text(appState.selectedLanguage.name)
                                .foregroundColor(.gray)

                            Image(systemName: "chevron.right")
                                .font(.caption)
                                .foregroundColor(.gray)
                        }
                    }
                    .sheet(isPresented: $showLanguageSelector) {
                        LanguageSelectView()
                            .environmentObject(appState)
                    }

                    Button(action: {
                        showAppearanceSelector = true
                    }) {
                        HStack {
                            Image(systemName: "paintbrush")
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))

                            Text("Appearance".localized)

                            Spacer()

                            // 显示当前选中的外观模式
                            Text(appState.selectedAppearance.name)
                                .foregroundColor(.gray)

                            Image(systemName: "chevron.right")
                                .font(.caption)
                                .foregroundColor(.gray)
                        }
                    }
                    .sheet(isPresented: $showAppearanceSelector) {
                        AppearanceSelectView()
                            .environmentObject(appState)
                    }

                    NavigationLink(destination: Text("Notifications settings will be available in future updates".localized).padding()) {
                        HStack {
                            Image(systemName: "bell")
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            Text("Notifications".localized)
                        }
                    }
                }

                // 隐私与安全
                Section(header: Text("Privacy & Security".localized)) {
                    NavigationLink(destination: Text("iCloud sync settings will be available in future updates".localized).padding()) {
                        HStack {
                            Image(systemName: "cloud")
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            Text("iCloud Sync".localized)
                        }
                    }

                    NavigationLink(destination: Text("Lock screen settings will be available in future updates".localized).padding()) {
                        HStack {
                            Image(systemName: "lock")
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            Text("Lock Screen".localized)
                        }
                    }

                    NavigationLink(destination: Text("Stealth mode settings will be available in future updates".localized).padding()) {
                        HStack {
                            Image(systemName: "eye.slash")
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            Text("Stealth Mode".localized)
                        }
                    }
                }

                // 关于
                Section(header: Text("About".localized)) {
                    NavigationLink(destination: Text("About MoodLog".localized).font(.title).padding()) {
                        HStack {
                            Image(systemName: "info.circle")
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            Text("Version & Info".localized)
                        }
                    }

                    NavigationLink(destination: Text("Privacy Policy will be available in future updates".localized).padding()) {
                        HStack {
                            Image(systemName: "hand.raised")
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            Text("Privacy Policy".localized)
                        }
                    }

                    NavigationLink(destination: Text("Terms of Use will be available in future updates".localized).padding()) {
                        HStack {
                            Image(systemName: "doc.text")
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            Text("Terms of Use".localized)
                        }
                    }
                }

                // 底部版本号
                Section {
                    HStack {
                        Spacer()
                        Text("MoodLog v1.0.0")
                            .font(.footnote)
                            .foregroundColor(.gray)
                        Spacer()
                    }
                }
                .listRowBackground(Color.clear)
            }
            .listStyle(InsetGroupedListStyle())
            .navigationTitle("Settings".localized)
            .id(forceRefresh) // 使用id强制视图刷新
            .sheet(isPresented: $showingProView) {
                ProView()
            }
            .onLanguageChange {
                // 语言变化时刷新视图
                forceRefresh.toggle()
            }
            .onAppear {
                // 更新Pro状态
                appState.updateProStatus()
            }
        }
    }
}

struct ProView: View {
    @Environment(\.presentationMode) var presentationMode
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showError = false
    @State private var purchaseSuccessful = false
    @StateObject private var storeManager = StoreManager()

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Image(systemName: "crown.fill")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 80, height: 80)
                    .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                    .padding()

                Text("Upgrade to Pro".localized)
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text("Unlock premium features and enhance your journal experience".localized)
                    .font(.headline)
                    .multilineTextAlignment(.center)
                    .foregroundColor(.secondary)
                    .padding(.horizontal)

                VStack(alignment: .leading, spacing: 15) {
                    FeatureRow(icon: "lock.open.fill", title: "Unlimited entries".localized, description: "Record as many moments as you want".localized)
                    FeatureRow(icon: "photo.on.rectangle", title: "Multiple images".localized, description: "Add up to 10 images per entry".localized)
                    FeatureRow(icon: "externaldrive.badge.checkmark", title: "Cloud backup".localized, description: "Never lose your memories".localized)
                    FeatureRow(icon: "wand.and.stars", title: "Advanced themes".localized, description: "Customize your journal experience".localized)
                    FeatureRow(icon: "chart.bar.fill", title: "Detailed analytics".localized, description: "Get insights into your mood patterns".localized)
                }
                .padding()
                .background(Color(UIColor.secondarySystemBackground))
                .cornerRadius(12)
                .padding(.horizontal)

                Spacer()

                VStack(spacing: 10) {
                    if isLoading {
                        ProgressView()
                            .scaleEffect(1.5)
                            .padding()
                    } else if purchaseSuccessful {
                        VStack(spacing: 10) {
                            Image(systemName: "checkmark.circle.fill")
                                .font(.largeTitle)
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))

                            Text("Thank you for subscribing!".localized)
                                .font(.headline)
                                .multilineTextAlignment(.center)
                                .padding()

                            Button(action: {
                                presentationMode.wrappedValue.dismiss()
                            }) {
                                Text("Continue".localized)
                                    .font(.headline)
                                    .foregroundColor(.white)
                                    .frame(maxWidth: .infinity)
                                    .padding()
                                    .background(Color(red: 0.15, green: 0.35, blue: 0.3))
                                    .cornerRadius(10)
                            }
                        }
                    } else {
                        // 月度订阅
                        Button(action: {
                            purchaseSubscription(productId: "com.sxyseo.moodfit.subscription.vip")
                        }) {
                            Text("$4.99 / Month".localized)
                                .font(.headline)
                                .foregroundColor(.white)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(Color(red: 0.15, green: 0.35, blue: 0.3))
                                .cornerRadius(10)
                        }

                        // 年度订阅
                        Button(action: {
                            purchaseSubscription(productId: "com.sxyseo.moodfit.subscription.svip")
                        }) {
                            Text("$39.99 / Year (Save 33%)".localized)
                                .font(.headline)
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(Color(UIColor.secondarySystemBackground))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 10)
                                        .stroke(Color(red: 0.15, green: 0.35, blue: 0.3), lineWidth: 2)
                                )
                        }

                        // 恢复购买
                        Button(action: {
                            restorePurchases()
                        }) {
                            Text("Restore Purchases".localized)
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                        .padding(.top)
                    }
                }
                .padding()
            }
            .navigationBarItems(leading: Button(action: {
                presentationMode.wrappedValue.dismiss()
            }) {
                Text("Cancel".localized)
            })
            .alert(isPresented: $showError) {
                Alert(
                    title: Text("Error".localized),
                    message: Text(errorMessage ?? "An error occurred during the purchase process.".localized),
                    dismissButton: .default(Text("OK".localized))
                )
            }
            .onAppear {
                storeManager.loadProducts()
            }
        }
    }

    // 处理订阅购买
    private func purchaseSubscription(productId: String) {
        guard let product = storeManager.products.first(where: { $0.productIdentifier == productId }) else {
            errorMessage = "Product not available.".localized
            showError = true
            return
        }

        isLoading = true

        storeManager.purchaseProduct(product: product) { success, error in
            DispatchQueue.main.async {
                isLoading = false

                if success {
                    // 购买成功
                    purchaseSuccessful = true
                    UserDefaults.standard.set(true, forKey: "isPro")
                } else if let error = error {
                    // 购买失败
                    errorMessage = error.localizedDescription
                    showError = true
                }
            }
        }
    }

    // 恢复购买
    private func restorePurchases() {
        isLoading = true

        storeManager.restorePurchases { success, error in
            DispatchQueue.main.async {
                isLoading = false

                if success {
                    // 恢复成功
                    purchaseSuccessful = true
                    UserDefaults.standard.set(true, forKey: "isPro")
                } else if let error = error {
                    // 恢复失败
                    errorMessage = error.localizedDescription
                    showError = true
                }
            }
        }
    }
}

struct FeatureRow: View {
    let icon: String
    let title: String
    let description: String

    var body: some View {
        HStack(spacing: 15) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                .frame(width: 30, height: 30)

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline)

                Text(description)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
        }
    }
}

struct LanguageSelectView: View {
    @Environment(\.presentationMode) var presentationMode
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationView {
            List(AppLanguage.allCases, id: \.self) { language in
                Button(action: {
                    if language != appState.selectedLanguage {
                        // 直接切换语言并关闭视图
                        appState.switchLanguage(to: language)
                        presentationMode.wrappedValue.dismiss() // 立即关闭视图
                    } else {
                        // 如果点击当前选中的语言，也关闭视图
                        presentationMode.wrappedValue.dismiss()
                    }
                }) {
                    HStack {
                        Text(language.name)

                        Spacer()

                        if language == appState.selectedLanguage {
                            Image(systemName: "checkmark")
                                .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                        }
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(PlainButtonStyle())
            }
            .navigationTitle("Choose Language".localized)
            .navigationBarItems(leading: Button(action: {
                presentationMode.wrappedValue.dismiss()
            }) {
                Text("Cancel".localized)
            })
        }
    }
}

// 月份选择器视图
struct MonthPickerView: View {
    @Binding var selectedMonth: Date
    @Binding var showMonthPicker: Bool
    @State private var tempYear: Int
    @State private var tempMonth: Int

    init(selectedMonth: Binding<Date>, showMonthPicker: Binding<Bool>) {
        self._selectedMonth = selectedMonth
        self._showMonthPicker = showMonthPicker

        let calendar = Calendar.current
        let components = calendar.dateComponents([.year, .month], from: selectedMonth.wrappedValue)
        self._tempYear = State(initialValue: components.year ?? Calendar.current.component(.year, from: Date()))
        self._tempMonth = State(initialValue: components.month ?? Calendar.current.component(.month, from: Date()))
    }

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // 年份选择器
                Picker("Year", selection: $tempYear) {
                    ForEach((tempYear-5)...(tempYear+5), id: \.self) { year in
                        Text("\(year)年").tag(year)
                    }
                }
                .pickerStyle(WheelPickerStyle())

                // 月份选择器
                Picker("Month", selection: $tempMonth) {
                    ForEach(1...12, id: \.self) { month in
                        Text("\(month)月").tag(month)
                    }
                }
                .pickerStyle(WheelPickerStyle())

                // 按钮
                HStack(spacing: 20) {
                    Button(action: {
                        // 回到今天
                        let today = Date()
                        let calendar = Calendar.current
                        tempYear = calendar.component(.year, from: today)
                        tempMonth = calendar.component(.month, from: today)
                    }) {
                        Text("Today".localized)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(UIColor.tertiarySystemBackground))
                            .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            .cornerRadius(10)
                    }

                    Button(action: {
                        // 应用选择的月份
                        var dateComponents = DateComponents()
                        dateComponents.year = tempYear
                        dateComponents.month = tempMonth
                        dateComponents.day = 1
                        if let date = Calendar.current.date(from: dateComponents) {
                            selectedMonth = date
                        }
                        showMonthPicker = false
                    }) {
                        Text("Confirm".localized)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(red: 0.15, green: 0.35, blue: 0.3))
                            .foregroundColor(.white)
                            .cornerRadius(10)
                    }
                }
                .padding()
            }
            .padding()
            .navigationTitle("Choose Month".localized)
            .navigationBarItems(leading: Button(action: {
                showMonthPicker = false
            }) {
                Text("Cancel".localized)
            })
        }
    }
}

// 年份选择器视图
struct YearPickerView: View {
    @Binding var selectedYear: Date
    @Binding var showYearPicker: Bool
    @State private var tempYear: Int

    init(selectedYear: Binding<Date>, showYearPicker: Binding<Bool>) {
        self._selectedYear = selectedYear
        self._showYearPicker = showYearPicker

        let calendar = Calendar.current
        let components = calendar.dateComponents([.year], from: selectedYear.wrappedValue)
        self._tempYear = State(initialValue: components.year ?? Calendar.current.component(.year, from: Date()))
    }

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // 年份选择器
                Picker("Year", selection: $tempYear) {
                    ForEach((tempYear-10)...(tempYear+10), id: \.self) { year in
                        Text("\(year)年").tag(year)
                    }
                }
                .pickerStyle(WheelPickerStyle())

                // 按钮
                HStack(spacing: 20) {
                    Button(action: {
                        // 回到今年
                        let today = Date()
                        let calendar = Calendar.current
                        tempYear = calendar.component(.year, from: today)
                    }) {
                        Text("This Year".localized)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(UIColor.tertiarySystemBackground))
                            .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            .cornerRadius(10)
                    }

                    Button(action: {
                        // 应用选择的年份
                        var dateComponents = DateComponents()
                        dateComponents.year = tempYear
                        dateComponents.month = 1
                        dateComponents.day = 1
                        if let date = Calendar.current.date(from: dateComponents) {
                            selectedYear = date
                        }
                        showYearPicker = false
                    }) {
                        Text("Confirm".localized)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color(red: 0.15, green: 0.35, blue: 0.3))
                            .foregroundColor(.white)
                            .cornerRadius(10)
                    }
                }
                .padding()
            }
            .padding()
            .navigationTitle("Choose Year".localized)
            .navigationBarItems(leading: Button(action: {
                showYearPicker = false
            }) {
                Text("Cancel".localized)
            })
        }
    }
}

// 外观模式选择视图
struct AppearanceSelectView: View {
    @Environment(\.presentationMode) var presentationMode
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationView {
            List {
                ForEach(AppearanceMode.allCases, id: \.self) { mode in
                    Button(action: {
                        if mode != appState.selectedAppearance {
                            // 切换外观模式并关闭视图
                            appState.switchAppearance(to: mode)
                        }
                        // 立即关闭视图
                        presentationMode.wrappedValue.dismiss()
                    }) {
                        HStack(spacing: 15) {
                            // 图标
                            ZStack {
                                Circle()
                                    .fill(mode == .dark ? Color(.systemGray5) : Color(.systemGray6))
                                    .frame(width: 36, height: 36)

                                Image(systemName: mode.iconName)
                                    .font(.system(size: 18))
                                    .foregroundColor(mode == .dark ? .white : Color(red: 0.15, green: 0.35, blue: 0.3))
                            }

                            // 名称和描述
                            VStack(alignment: .leading, spacing: 3) {
                                Text(mode.displayName)
                                    .foregroundColor(.primary)
                                    .font(.body)

                                if mode == .system {
                                    Text("Follow system settings".localized)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }

                            Spacer()

                            // 选中标记
                            if mode == appState.selectedAppearance {
                                Image(systemName: "checkmark")
                                    .font(.system(size: 16, weight: .bold))
                                    .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                            }
                        }
                        .contentShape(Rectangle())
                        .padding(.vertical, 8)
                    }
                    .buttonStyle(PlainButtonStyle())
                }
            }
            .navigationTitle("Appearance".localized)
            .navigationBarItems(leading: Button(action: {
                presentationMode.wrappedValue.dismiss()
            }) {
                Text("Cancel".localized)
            })
        }
    }
}

// 处理应用内购买的管理器
class StoreManager: NSObject, ObservableObject, SKProductsRequestDelegate, SKPaymentTransactionObserver {
    @Published var products: [SKProduct] = []
    private var productsRequest: SKProductsRequest?
    private var completionHandler: ((Bool, Error?) -> Void)?

    // 更新产品ID以匹配App Store Connect中的配置
    private let productIdentifiers = Set([
        "com.sxyseo.moodfit.subscription.vip",  // 月度订阅
        "com.sxyseo.moodfit.subscription.svip"    // 年度订阅
    ])

    override init() {
        super.init()
        SKPaymentQueue.default().add(self)
    }

    deinit {
        SKPaymentQueue.default().remove(self)
    }

    // 加载可购买的产品
    func loadProducts() {
        print("开始加载产品...")
        productsRequest = SKProductsRequest(productIdentifiers: productIdentifiers)
        productsRequest?.delegate = self
        productsRequest?.start()
    }

    // 处理产品请求响应
    func productsRequest(_ request: SKProductsRequest, didReceive response: SKProductsResponse) {
        DispatchQueue.main.async {
            self.products = response.products

            if self.products.isEmpty {
                print("警告：没有找到可用的产品")
                print("无效的产品ID：\(response.invalidProductIdentifiers)")
            } else {
                print("成功加载产品：\(self.products.count)个")
                for product in self.products {
                    print("产品ID: \(product.productIdentifier)")
                    print("产品名称: \(product.localizedTitle)")
                    print("产品描述: \(product.localizedDescription)")
                    print("产品价格: \(product.price)")
                    print("产品周期: \(product.subscriptionPeriod)")
                    print("------------------------")
                }
            }
        }
    }

    // 处理产品请求错误
    func request(_ request: SKRequest, didFailWithError error: Error) {
        print("产品请求失败：\(error.localizedDescription)")
        DispatchQueue.main.async {
            self.completionHandler?(false, error)
        }
    }

    // 购买产品
    func purchaseProduct(product: SKProduct, completion: @escaping (Bool, Error?) -> Void) {
        if SKPaymentQueue.canMakePayments() {
            print("开始购买产品：\(product.productIdentifier)")
            completionHandler = completion
            let payment = SKPayment(product: product)
            SKPaymentQueue.default().add(payment)
        } else {
            let error = NSError(domain: "StoreManager", code: 0, userInfo: [NSLocalizedDescriptionKey: "In-app purchases are not allowed".localized])
            print("无法进行应用内购买：\(error.localizedDescription)")
            completion(false, error)
        }
    }

    // 恢复购买
    func restorePurchases(completion: @escaping (Bool, Error?) -> Void) {
        print("开始恢复购买...")
        completionHandler = completion
        SKPaymentQueue.default().restoreCompletedTransactions()
    }

    // 处理支付队列变化
    func paymentQueue(_ queue: SKPaymentQueue, updatedTransactions transactions: [SKPaymentTransaction]) {
        for transaction in transactions {
            print("交易状态更新：\(transaction.transactionState.rawValue)")
            print("交易ID：\(transaction.transactionIdentifier ?? "N/A")")
            print("产品ID：\(transaction.payment.productIdentifier)")

            switch transaction.transactionState {
            case .purchased:
                print("购买成功")
                completeTransaction(transaction)

            case .failed:
                print("购买失败：\(transaction.error?.localizedDescription ?? "未知错误")")
                failedTransaction(transaction)

            case .restored:
                print("恢复购买成功")
                restoreTransaction(transaction)

            case .deferred, .purchasing:
                print("交易正在处理中...")
                break

            @unknown default:
                print("未知交易状态")
                break
            }
        }
    }

    // 完成交易
    private func completeTransaction(_ transaction: SKPaymentTransaction) {
        SKPaymentQueue.default().finishTransaction(transaction)
        DispatchQueue.main.async {
            print("交易完成，更新用户状态")
            UserDefaults.standard.set(true, forKey: "isPro")
            self.completionHandler?(true, nil)
        }
    }

    // 失败交易
    private func failedTransaction(_ transaction: SKPaymentTransaction) {
        SKPaymentQueue.default().finishTransaction(transaction)
        DispatchQueue.main.async {
            print("交易失败，显示错误信息")
            self.completionHandler?(false, transaction.error)
        }
    }

    // 恢复交易
    private func restoreTransaction(_ transaction: SKPaymentTransaction) {
        SKPaymentQueue.default().finishTransaction(transaction)
        DispatchQueue.main.async {
            print("恢复交易成功，更新用户状态")
            UserDefaults.standard.set(true, forKey: "isPro")
            self.completionHandler?(true, nil)
        }
    }

    // 恢复购买完成
    func paymentQueueRestoreCompletedTransactionsFinished(_ queue: SKPaymentQueue) {
        DispatchQueue.main.async {
            if queue.transactions.isEmpty {
                print("没有找到可恢复的购买")
                self.completionHandler?(false, NSError(domain: "StoreManager", code: 1, userInfo: [NSLocalizedDescriptionKey: "No purchases to restore".localized]))
            } else {
                print("成功恢复购买")
                self.completionHandler?(true, nil)
            }
        }
    }

    // 恢复购买失败
    func paymentQueue(_ queue: SKPaymentQueue, restoreCompletedTransactionsFailedWithError error: Error) {
        print("恢复购买失败：\(error.localizedDescription)")
        DispatchQueue.main.async {
            self.completionHandler?(false, error)
        }
    }
}
