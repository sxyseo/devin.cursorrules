// swift-tools-version:5.5
import PackageDescription

let package = Package(
    name: "MoodLog",
    defaultLocalization: "en",
    platforms: [
        .iOS(.v15),
        .macOS(.v12)
    ],
    products: [
        .library(
            name: "MoodLog",
            targets: ["MoodLog"]),
    ],
    dependencies: [
        // 暂时注释掉 Firebase 依赖
        // .package(url: "https://github.com/firebase/firebase-ios-sdk.git", .upToNextMajor(from: "10.0.0"))  
    ],
    targets: [
        .target(
            name: "MoodLog",
            dependencies: [
                // 暂时注释掉 Firebase 产品依赖
                // .product(name: "FirebaseCore", package: "firebase-ios-sdk"),
                // .product(name: "FirebaseAnalytics", package: "firebase-ios-sdk"),
                // .product(name: "FirebaseAuth", package: "firebase-ios-sdk"),
                // .product(name: "FirebaseFirestore", package: "firebase-ios-sdk"),
                // .product(name: "FirebaseFirestoreSwift", package: "firebase-ios-sdk")
            ],
            path: "Sources/MoodLog",
            resources: [
                .process("Resources"),
                .process("Assets.xcassets"),
                .process("Preview Content"),
                .process("LaunchScreen.storyboard")
            ]
        ),
        .testTarget(
            name: "MoodLogTests",
            dependencies: ["MoodLog"],
            path: "Tests/MoodLogTests"
        ),
    ]
) 
