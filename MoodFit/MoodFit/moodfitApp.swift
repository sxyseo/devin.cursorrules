//
//  MoodLogApp.swift
//  MoodLog
//
//  Created by abel on 2025/3/28.
//

import SwiftUI
import Foundation
#if canImport(UIKit)
import UIKit
#endif

// 使用SwiftUI应用入口点
@main
struct MoodLogApp: App {
    init() {
        // 直接初始化LocalizationHelper
        let helper = LocalizationHelper.shared
        let currentLanguage = helper.getCurrentLanguage()

        // 应用保存的外观模式设置
        applyAppearanceSettings()

        // 预热本地化系统
        _ = Bundle.main.localizedString(forKey: "MoodLog", value: nil, table: nil)

        print("应用启动，已初始化语言: \(currentLanguage)")
    }

    // 应用保存的外观模式设置
    private func applyAppearanceSettings() {
        #if canImport(UIKit)
        if let savedValue = UserDefaults.standard.object(forKey: "selectedAppearance") as? Int {
            let userInterfaceStyle: UIUserInterfaceStyle

            switch savedValue {
            case 1: // light
                userInterfaceStyle = .light
            case 2: // dark
                userInterfaceStyle = .dark
            default: // system or unknown
                userInterfaceStyle = .unspecified
            }

            // 应用外观模式
            DispatchQueue.main.async {
                UIApplication.shared.windows.forEach { window in
                    window.overrideUserInterfaceStyle = userInterfaceStyle
                }
            }

            print("已应用保存的外观模式设置: \(savedValue)")
        }
        #endif
    }

    var body: some Scene {
        WindowGroup {
            // 显示主视图
            ContentView()
        }
    }
}
