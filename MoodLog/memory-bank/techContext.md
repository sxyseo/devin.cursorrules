# 技术背景

## 技术栈

### 主要技术
- **编程语言**：Swift 5.9+
- **UI 框架**：SwiftUI + UIKit（混合架构）
- **数据存储**：CoreData + SQLite
- **本地加密**：iOS Keychain
- **健康数据**：HealthKit

### 辅助技术
- **AI 模型**：CoreML + 轻量化 BERT 模型
- **图表可视化**：Swift Charts（iOS 16+）或第三方图表库
- **异步编程**：Swift Concurrency (async/await)
- **反应式编程**：Combine 框架
- **用户分析**：Firebase Analytics（匿名统计）

## 开发环境

### 开发工具
- **IDE**：Xcode 15+
- **依赖管理**：Swift Package Manager
- **版本控制**：Git
- **CI/CD**：GitHub Actions 或 Fastlane

### 开发设置
- **最低 iOS 版本**：iOS 15+（覆盖率 >95%）
- **设备兼容性**：iPhone 和 iPad（通用应用）
- **目标架构**：ARM64

### 测试环境
- **单元测试**：XCTest 框架
- **UI 测试**：XCUITest
- **性能测试**：Instruments

## 技术约束

### 硬性约束
1. **设备兼容性**：
   - **必须支持** iOS 15+ 设备
   - **必须适配** iPhone 和 iPad 各种屏幕尺寸

2. **性能要求**：
   - 情绪分析响应时间 ≤800ms（iPhone 12 及以上机型）
   - 本地数据加密/解密速度 >50 条/秒
   - 应用启动时间 <1.5s

3. **安全要求**：
   - 所有日记内容必须加密存储
   - 必须支持 Face ID/Touch ID 验证
   - 禁止用户数据上传到云端

### 软性约束
1. **应用体积**：
   - 目标安装包大小 <50MB
   - AI 模型体积 <10MB

2. **电池影响**：
   - 后台处理最小化
   - 避免持续高 CPU 使用率

3. **网络依赖**：
   - 核心功能必须可在离线状态下使用
   - 仅统计分析和可选功能依赖网络

## 依赖关系

### 核心依赖

#### iOS 系统框架
- **SwiftUI**：用户界面构建
- **UIKit**：复杂自定义组件
- **CoreData**：本地数据存储
- **HealthKit**：健康数据访问
- **LocalAuthentication**：生物识别认证
- **Security**：数据加密
- **CoreML**：机器学习模型部署
- **Combine**：反应式编程

#### 第三方库
- **Charts**（或 Swift Charts）：数据可视化
- **Firebase Analytics**：用户行为分析
- **KeychainAccess**：简化 Keychain 操作

### 可选依赖
- **IQKeyboardManager**：键盘处理
- **SDWebImage**：图片缓存和加载
- **Lottie**：高级动画效果

## 技术决策记录

### TDR-001：采用 SwiftUI + UIKit 混合架构
- **背景**：需要平衡开发效率和 UI 定制能力
- **决策**：主界面使用 SwiftUI，复杂组件使用 UIKit
- **替代方案**：纯 SwiftUI 或纯 UIKit
- **结果**：混合架构满足开发效率和定制需求

### TDR-002：使用 CoreML 进行本地情绪分析
- **背景**：需要保护用户隐私同时提供情绪分析功能
- **决策**：使用 CoreML 部署轻量级 BERT 模型
- **替代方案**：云端 API 处理或简单关键词匹配
- **结果**：既保护隐私又提供准确分析

### TDR-003：禁用 iCloud 同步
- **背景**：避免隐私和合规风险
- **决策**：所有数据本地存储，不使用 iCloud 同步
- **替代方案**：加密后 iCloud 同步
- **结果**：简化合规流程，增强隐私保护

## API 和集成

### 内部 API
以下是应用内主要模块间的 API 接口：

```swift
// 日记管理器 API
protocol JournalManagerProtocol {
    func createEntry(content: String, mood: MoodType, images: [UIImage]?) async throws -> JournalEntry
    func getEntries(from: Date, to: Date) async throws -> [JournalEntry]
    func updateEntry(_ entry: JournalEntry) async throws
    func deleteEntry(_ entry: JournalEntry) async throws
}

// 情绪分析器 API
protocol MoodAnalyzerProtocol {
    func analyzeText(_ text: String) async -> MoodScore
    func generateMoodReport(from: Date, to: Date) async throws -> MoodReport
    func getMoodTrend(days: Int) async throws -> MoodTrend
}

// 健康数据管理器 API
protocol HealthDataManagerProtocol {
    func requestAuthorization() async throws
    func fetchStepCount(from: Date, to: Date) async throws -> [StepData]
    func fetchHeartRate(from: Date, to: Date) async throws -> [HeartRateData]
    func correlateWithMood(healthData: HealthDataType, moodData: [MoodEntry]) async -> CorrelationResult
}
```

### 外部集成
- **Apple HealthKit**：用于读取健康数据
- **Firebase**：用于匿名分析和崩溃报告
- **Device Biometrics**：Face ID/Touch ID 集成 