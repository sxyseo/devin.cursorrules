import SwiftUI
#if os(iOS)
import UIKit
import PhotosUI
#endif

struct JournalEntryEditorView: View {
    @Environment(\.presentationMode) var presentationMode
    @State private var selectedMood: Int = 2 // 默认是"一般"心情
    @State private var content: String = ""
    // 暂时注释掉 UIImage 相关代码
    // #if os(iOS)
    // @State private var selectedImage: UIImage? = nil
    // #endif
    @State private var isImagePickerPresented = false
    @State private var selectedDate: Date
    @FocusState private var isFocused: Bool
    @EnvironmentObject var journalStore: JournalEntryStore
    @State private var isEditing: Bool
    @State private var entryId: UUID

    init(date: Date = Date(), isEditing: Bool = false, entryId: UUID = UUID(), initialMood: Int = 2, initialContent: String = "", initialDate: Date? = nil) {
        self._selectedDate = State(initialValue: initialDate ?? date)
        self._isEditing = State(initialValue: isEditing)
        self._entryId = State(initialValue: entryId)
        self._selectedMood = State(initialValue: initialMood)
        self._content = State(initialValue: initialContent)

        print("初始化日记编辑视图，选定日期：\(self._selectedDate.wrappedValue)")
    }

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // 心情选择器
                MoodSelector(selectedMood: $selectedMood)
                    .padding(.top, 10)

                Divider()

                // 内容编辑区域
                // 暂时注释掉 UIImage 相关代码
                // #if os(iOS)
                // if let image = selectedImage {
                //     Image(uiImage: image)
                //         .resizable()
                //         .scaledToFit()
                //         .frame(maxHeight: 200)
                //         .cornerRadius(10)
                //         .padding(.horizontal)
                //         .overlay(
                //             Button(action: {
                //                 selectedImage = nil
                //             }) {
                //                 Image(systemName: "xmark.circle.fill")
                //                     .font(.title)
                //                     .foregroundColor(.white)
                //                     .shadow(radius: 2)
                //             }
                //             .padding(8),
                //             alignment: .topTrailing
                //         )
                // }
                // #endif

                ZStack(alignment: .topLeading) {
                    if content.isEmpty {
                        Text("How do you feel today?".localized)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 12)
                            .foregroundColor(.gray)
                    }

                    TextEditor(text: $content)
                        .focused($isFocused)
                        .padding(4)
                }
                .frame(maxHeight: .infinity)

                // 底部工具栏
                HStack {
                    // 暂时注释掉 UIImage 相关代码
                    // #if os(iOS)
                    // // 添加图片按钮
                    // Button(action: {
                    //     isImagePickerPresented = true
                    // }) {
                    //     Image(systemName: "photo")
                    //         .font(.title2)
                    //         .foregroundColor(Color(red: 0.15, green: 0.35, blue: 0.3))
                    //         .frame(width: 44, height: 44)
                    //         .background(Color(.secondarySystemBackground))
                    //         .cornerRadius(22)
                    //         .shadow(color: Color.black.opacity(0.1), radius: 3, x: 0, y: 1)
                    // }
                    // .sheet(isPresented: $isImagePickerPresented) {
                    //     ImagePicker(selectedImage: $selectedImage)
                    // }
                    // #endif

                    Spacer()

                    // 保存按钮
                    Button(action: {
                        if isEditing {
                            // 更新条目
                            updateEntry()
                        } else {
                            // 创建新条目
                            saveEntry()
                        }
                        hideKeyboard()

                        // 确保UI刷新并等待状态更新
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                            presentationMode.wrappedValue.dismiss()
                        }
                    }) {
                        Text(isEditing ? "Update".localized : "Save".localized)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                            .padding(.horizontal, 30)
                            .padding(.vertical, 12)
                            .background(Color(red: 0.15, green: 0.35, blue: 0.3))
                            .cornerRadius(25)
                            .shadow(color: Color.black.opacity(0.1), radius: 3, x: 0, y: 1)
                    }
                    .disabled(content.isEmpty)
                    .opacity(content.isEmpty ? 0.6 : 1)
                }
                .padding(.horizontal)
                .padding(.bottom, 10)
            }
            .padding()
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel".localized) {
                        presentationMode.wrappedValue.dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    if isFocused {
                        Button("Done".localized) {
                            hideKeyboard()
                        }
                    }
                }
            }
            .navigationTitle(isEditing ? "Edit Entry".localized : "New Entry".localized)
            .onTapGesture {
                hideKeyboard()
            }
        }
    }

    // 保存记录
    func saveEntry() {
        // 创建合并了日期和时间的完整日期
        let calendar = Calendar.current
        let timeComponents = calendar.dateComponents([.hour, .minute], from: Date())
        let dateComponents = calendar.dateComponents([.year, .month, .day], from: selectedDate)
        var mergedComponents = DateComponents()
        mergedComponents.year = dateComponents.year
        mergedComponents.month = dateComponents.month
        mergedComponents.day = dateComponents.day
        mergedComponents.hour = timeComponents.hour
        mergedComponents.minute = timeComponents.minute

        let combinedDate = calendar.date(from: mergedComponents) ?? Date()
        print("保存日记，选定日期: \(selectedDate), 合并后日期: \(combinedDate)")

        // 保存日记条目
        journalStore.addEntry(
            mood: selectedMood,
            moodType: MoodType(rawValue: Int16(selectedMood)) ?? .neutral,
            content: content,
            date: combinedDate
        )

        // 确保UI更新
        DispatchQueue.main.async {
            journalStore.objectWillChange.send()
        }
    }

    // 更新记录
    func updateEntry() {
        // 创建合并了日期和时间的完整日期
        let calendar = Calendar.current
        let timeComponents = calendar.dateComponents([.hour, .minute], from: Date())
        let dateComponents = calendar.dateComponents([.year, .month, .day], from: selectedDate)
        var mergedComponents = DateComponents()
        mergedComponents.year = dateComponents.year
        mergedComponents.month = dateComponents.month
        mergedComponents.day = dateComponents.day
        mergedComponents.hour = timeComponents.hour
        mergedComponents.minute = timeComponents.minute

        let combinedDate = calendar.date(from: mergedComponents) ?? Date()

        // 更新日记条目
        journalStore.updateEntry(
            id: entryId,
            mood: selectedMood,
            moodType: MoodType(rawValue: Int16(selectedMood)) ?? .neutral,
            content: content,
            date: combinedDate
        )

        // 确保UI更新
        DispatchQueue.main.async {
            journalStore.objectWillChange.send()
        }
    }

    // 隐藏键盘
    func hideKeyboard() {
        isFocused = false
        #if os(iOS)
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
        #endif
    }
}

// 暂时注释掉 ImagePicker
// #if os(iOS)
// struct ImagePicker: UIViewControllerRepresentable {
//     @Binding var selectedImage: UIImage?
//     @Environment(\.presentationMode) private var presentationMode
//     
//     func makeUIViewController(context: Context) -> PHPickerViewController {
//         var config = PHPickerConfiguration()
//         config.filter = .images
//         let picker = PHPickerViewController(configuration: config)
//         picker.delegate = context.coordinator
//         return picker
//     }
//     
//     func updateUIViewController(_ uiViewController: PHPickerViewController, context: Context) {}
//     
//     func makeCoordinator() -> Coordinator {
//         Coordinator(self)
//     }
//     
//     class Coordinator: NSObject, PHPickerViewControllerDelegate {
//         let parent: ImagePicker
//         
//         init(_ parent: ImagePicker) {
//             self.parent = parent
//         }
//         
//         func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
//             parent.presentationMode.wrappedValue.dismiss()
//             
//             guard let provider = results.first?.itemProvider else { return }
//             
//             if provider.canLoadObject(ofClass: UIImage.self) {
//                 provider.loadObject(ofClass: UIImage.self) { image, _ in
//                     DispatchQueue.main.async {
//                         self.parent.selectedImage = image as? UIImage
//                     }
//                 }
//             }
//         }
//     }
// }
// #endif 