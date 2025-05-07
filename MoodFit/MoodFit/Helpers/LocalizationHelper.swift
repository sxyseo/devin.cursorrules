//
//  LocalizationHelper.swift
//  MoodLog
//
//  Created by abel on 2025/3/29.
//

import Foundation
import SwiftUI

// 使用此类型别名避免与ContentView中的AppLanguage冲突
typealias LanguageCode = String

// 定义语言改变通知名称
extension Notification.Name {
    static let languageDidChange = Notification.Name("languageDidChange")
}

// 自定义Bundle扩展，允许即时切换语言
class BundleEx: Bundle, @unchecked Sendable {
    // 用于保存原始的bundle.localizedString方法
    static private var originalBundle: Bundle?
    // 当前语言
    static private var currentLanguage: String?

    // 重写localizedString方法
    override func localizedString(forKey key: String, value: String?, table tableName: String?) -> String {
        // 先从当前语言的资源中获取字符串
        if let currentLanguage = BundleEx.currentLanguage,
           let path = Bundle.main.path(forResource: currentLanguage, ofType: "lproj"),
           let languageBundle = Bundle(path: path) {
            return languageBundle.localizedString(forKey: key, value: value, table: tableName)
        }
        // 否则使用原始方法
        return super.localizedString(forKey: key, value: value, table: tableName)
    }

    // 设置当前语言
    static func setLanguage(_ language: String) {
        // 保存当前语言
        currentLanguage = language

        // 如果还没有保存原始bundle，先保存
        if originalBundle == nil {
            originalBundle = Bundle.main

            // 只有第一次才需要交换
            object_setClass(Bundle.main, BundleEx.self)
        }

        // 立即发送通知
        DispatchQueue.main.async {
            NotificationCenter.default.post(name: .languageDidChange, object: language)
            print("已在BundleEx中更新语言: \(language)")
        }
    }
}

class LocalizationHelper {

    static let shared = LocalizationHelper()

    private init() {
        // 初始化时检查是否已经设置语言
        let currentLanguage = getCurrentLanguage()
        BundleEx.setLanguage(currentLanguage)
    }

    // 当前应用程序的语言
    var currentLanguage: String {
        return getCurrentLanguage()
    }

    // 设置应用程序的语言
    func setLanguage(_ languageCode: String) {
        UserDefaults.standard.set([languageCode], forKey: "AppleLanguages")
        UserDefaults.standard.synchronize()

        // 使用BundleEx立即切换语言
        BundleEx.setLanguage(languageCode)

        // 立即发送语言改变通知，使用主线程确保UI立即更新
        DispatchQueue.main.async {
            NotificationCenter.default.post(name: .languageDidChange, object: languageCode)
            print("语言已切换到：\(languageCode)，已发送通知")
        }
    }

    // 获取当前语言
    func getCurrentLanguage() -> String {
        // 首先尝试从UserDefaults获取
        if let savedLanguage = UserDefaults.standard.string(forKey: "selectedLanguage") {
            if let appLanguage = Int(savedLanguage), let language = [0: "zh-Hans", 1: "en", 2: "ja"][appLanguage] {
                return language
            }
        }

        // 否则获取系统语言
        let currentLocale = Locale.current

        if #available(iOS 16, *) {
            return currentLocale.language.languageCode?.identifier ?? "en"
        } else {
            // iOS 16之前的版本使用
            return currentLocale.languageCode ?? "en"
        }
    }

    // 获取本地化字符串
    func localizedString(for key: String, comment: String = "") -> String {
        return NSLocalizedString(key, comment: comment)
    }

    // 重载当前所有Bundle的本地化资源
    func reloadLocalizationBundle() {
        // 强制刷新本地化资源
        let currentLanguage = getCurrentLanguage()
        BundleEx.setLanguage(currentLanguage)

        // 使用主线程确保UI立即更新
        DispatchQueue.main.async {
            NotificationCenter.default.post(name: .languageDidChange, object: nil)
        }
    }
}

// 为String添加扩展，简化本地化字符串的获取
extension String {
    var localized: String {
        return LocalizationHelper.shared.localizedString(for: self)
    }

    func localized(with comment: String) -> String {
        return LocalizationHelper.shared.localizedString(for: self, comment: comment)
    }

    // 通用
    static let systemMode = "System"
    static let lightMode = "Light"
    static let darkMode = "Dark"
    static let useDeviceSettings = "Use Device Settings"
    static let lightModeText = "Light Mode"
    static let darkModeText = "Dark Mode"
    static let followSystemSettings = "Follow system settings"
    static let chooseAppearance = "Choose Appearance"

    // 多语言支持
    static func getLocalizedAppearanceName(for mode: Int) -> String {
        switch mode {
        case 0: // system
            return LocalizationHelper.shared.currentLanguage.starts(with: "zh") ? "跟随系统" :
                   LocalizationHelper.shared.currentLanguage.starts(with: "ja") ? "システム" : "System"
        case 1: // light
            return LocalizationHelper.shared.currentLanguage.starts(with: "zh") ? "浅色模式" :
                   LocalizationHelper.shared.currentLanguage.starts(with: "ja") ? "ライトモード" : "Light"
        case 2: // dark
            return LocalizationHelper.shared.currentLanguage.starts(with: "zh") ? "深色模式" :
                   LocalizationHelper.shared.currentLanguage.starts(with: "ja") ? "ダークモード" : "Dark"
        default:
            return "Unknown"
        }
    }

    static func getLocalizedAppearanceDisplayName(for mode: Int) -> String {
        switch mode {
        case 0: // system
            return LocalizationHelper.shared.currentLanguage.starts(with: "zh") ? "跟随系统设置" :
                   LocalizationHelper.shared.currentLanguage.starts(with: "ja") ? "デバイス設定に従う" : "Use Device Settings"
        case 1: // light
            return LocalizationHelper.shared.currentLanguage.starts(with: "zh") ? "浅色模式" :
                   LocalizationHelper.shared.currentLanguage.starts(with: "ja") ? "ライトモード" : "Light Mode"
        case 2: // dark
            return LocalizationHelper.shared.currentLanguage.starts(with: "zh") ? "深色模式" :
                   LocalizationHelper.shared.currentLanguage.starts(with: "ja") ? "ダークモード" : "Dark Mode"
        default:
            return "Unknown"
        }
    }
}

// 本地化视图修饰符
struct LocalizedStringKey: ViewModifier {
    let key: String

    func body(content: Content) -> some View {
        content
            .accessibility(label: Text(NSLocalizedString(key, comment: "")))
    }
}

// 添加视图扩展，使视图可以监听语言变化
extension View {
    func onLanguageChange(perform action: @escaping () -> Void) -> some View {
        self.onReceive(NotificationCenter.default.publisher(for: .languageDidChange)) { _ in
            action()
        }
    }
}
