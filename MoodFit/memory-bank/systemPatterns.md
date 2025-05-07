# 系统模式

## 系统架构

MoodLog 采用标准的 iOS 应用架构，遵循 Apple 推荐的最佳实践。系统架构如下：

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    表现层 (Presentation)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │  日记视图   │  │ 情绪分析视图 │  │  设置视图   │ ...  │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
├─────────────────────────────────────────────────────────┤
│                    业务逻辑层 (Business Logic)              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ 日记管理器  │  │ 情绪分析器   │  │ 健身数据管理 │ ...  │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
├─────────────────────────────────────────────────────────┤
│                    数据层 (Data)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ CoreData    │  │ HealthKit   │  │ 加密存储     │ ...  │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────┘
```

## 关键技术决策

### 1. 采用 SwiftUI + UIKit 混合架构

**决策**：主界面使用 SwiftUI 构建，复杂自定义组件使用 UIKit 并通过 UIViewRepresentable 桥接。

**原因**：
- SwiftUI 简化界面构建流程，降低开发复杂度
- 对于复杂的定制视图（如情绪热力图），UIKit 提供更精细的控制
- 混合架构确保既能获得 SwiftUI 的快速开发优势，又不受其限制

### 2. 本地数据存储与加密

**决策**：使用 CoreData 进行本地数据存储，结合 iOS Keychain 实现数据加密。

**原因**：
- 避免云存储带来的隐私和合规风险
- CoreData 与 iOS 生态系统深度集成，性能优异
- Keychain 提供系统级安全保障，简化加密实现

### 3. 端侧 AI 模型部署

**决策**：使用 CoreML 部署轻量化 BERT 模型进行情绪分析。

**原因**：
- 本地处理确保用户数据隐私
- 减少网络依赖，提升响应速度
- 轻量化模型（<10MB）不会显著增加应用体积

### 4. 数据可视化引擎

**决策**：使用 Swift Charts（iOS 16+）或第三方图表库进行数据可视化。

**原因**：
- Swift Charts 与 SwiftUI 原生集成，性能优异
- 支持丰富的图表类型，满足情绪热力图和趋势报告需求
- 提供良好的交互体验

## 设计模式

MoodLog 应用中采用了以下主要设计模式：

### 1. MVVM (Model-View-ViewModel)

用于分离 UI 逻辑与业务逻辑：
- **Model**：封装数据结构和业务规则（如 `JournalEntry`, `MoodAnalysis` 等）
- **View**：纯粹的 UI 层，负责数据展示与用户交互
- **ViewModel**：连接 Model 和 View，处理 UI 状态和业务逻辑

### 2. 依赖注入

通过构造函数或属性注入方式，将服务和管理器注入到需要的组件中：
```swift
class MoodAnalyticsViewModel {
    private let moodAnalyzer: MoodAnalyzerProtocol
    private let healthDataManager: HealthDataManagerProtocol
    
    init(moodAnalyzer: MoodAnalyzerProtocol, healthDataManager: HealthDataManagerProtocol) {
        self.moodAnalyzer = moodAnalyzer
        self.healthDataManager = healthDataManager
    }
    // ...
}
```

### 3. 策略模式

用于情绪分析算法的可替换实现：
```swift
protocol MoodAnalysisStrategy {
    func analyzeMood(from text: String) -> MoodScore
}

class BERTMoodAnalysis: MoodAnalysisStrategy {
    func analyzeMood(from text: String) -> MoodScore {
        // 使用 BERT 模型分析
    }
}

class KeywordMoodAnalysis: MoodAnalysisStrategy {
    func analyzeMood(from text: String) -> MoodScore {
        // 使用关键词匹配分析
    }
}
```

### 4. 观察者模式

用于组件间通信和状态同步，主要通过 Combine 框架实现：
```swift
class MoodTracker {
    var moodPublisher = PassthroughSubject<MoodEntry, Never>()
    
    func recordMood(_ mood: MoodEntry) {
        // 存储心情记录
        moodPublisher.send(mood)
    }
}
```

## 组件关系

MoodLog 的主要组件及其关系如下：

### 核心组件

1. **日记管理器 (JournalManager)**
   - 负责日记条目的创建、读取、更新和删除
   - 管理日记内容的加密存储
   - 与 CoreData 存储层交互

2. **情绪分析器 (MoodAnalyzer)**
   - 分析文本情绪倾向
   - 生成情绪评分
   - 创建情绪热力图和趋势报告

3. **健康数据管理器 (HealthDataManager)**
   - 与 HealthKit 交互获取健康数据
   - 处理步数、心率、睡眠等数据
   - 分析运动与情绪的相关性

4. **勋章系统 (AchievementSystem)**
   - 跟踪用户连续记录天数
   - 管理勋章解锁条件和状态
   - 提供奖励（如主题解锁）

5. **安全管理器 (SecurityManager)**
   - 管理生物识别认证
   - 处理数据加密/解密
   - 实现伪装模式功能

### 组件交互图

```
                  ┌─────────────────┐
                  │     用户界面     │
                  └───────┬─────────┘
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
┌──────────────────────┐    ┌─────────────────────┐
│     日记管理器        │◄───►│     情绪分析器      │
└──────────┬───────────┘    └──────────┬──────────┘
           │                           │
           │                           │
           ▼                           ▼
┌──────────────────────┐    ┌─────────────────────┐
│     安全管理器        │    │    健康数据管理器    │
└──────────┬───────────┘    └──────────┬──────────┘
           │                           │
           └──────────────┬────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │    勋章系统     │
                 └─────────────────┘
```

## 数据流

MoodLog 中的主要数据流如下：

1. **日记记录流程**：
   - 用户创建日记 → 选择情绪标签 → 日记管理器存储记录 → 情绪分析器处理内容 → 更新情绪统计 → 勋章系统检查成就

2. **健身-情绪分析流程**：
   - 健康数据管理器获取运动数据 → 与情绪数据关联 → 分析相关性 → 生成报告 → 展示给用户

3. **隐私保护流程**：
   - 应用启动 → 安全管理器验证身份 → 成功后解密数据 → 允许访问应用功能 
