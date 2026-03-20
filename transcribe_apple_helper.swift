#!/usr/bin/env swift
/// Apple SFSpeechRecognizer helper
/// Usage: TranscribeHelper <audio_path> <output_json_path>

import Foundation
import Speech

func main() {
    // 過濾 open 啟動時插入的 -psn_XXXXX 參數
    let args = CommandLine.arguments.filter { !$0.hasPrefix("-psn_") }
    guard args.count >= 3 else {
        fputs("Usage: TranscribeHelper <audio_path> <output_json>\nReceived: \(CommandLine.arguments)\n", stderr)
        exit(1)
    }

    let audioPath = args[1]
    let outputPath = args[2]
    let logPath = outputPath + ".log"
    var logLines: [String] = ["start: \(Date())", "args: \(args)"]

    func log(_ msg: String) {
        logLines.append(msg)
        fputs(msg + "\n", stderr)
    }

    // --- 確認檔案存在 ---
    guard FileManager.default.fileExists(atPath: audioPath) else {
        log("錯誤：找不到音訊檔 \(audioPath)")
        try? logLines.joined(separator: "\n").write(toFile: logPath, atomically: true, encoding: .utf8)
        exit(1)
    }
    log("audio file found: \(audioPath)")

    // --- 授權 ---
    var authDone = false
    var authStatus: SFSpeechRecognizerAuthorizationStatus = .notDetermined

    SFSpeechRecognizer.requestAuthorization { status in
        authStatus = status
        authDone = true
    }

    // Spin RunLoop until auth completes (max 30s)
    let authDeadline = Date().addingTimeInterval(30)
    while !authDone && Date() < authDeadline {
        RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.1))
    }
    log("AUTH_STATUS:\(authStatus.rawValue)")

    guard authStatus == .authorized else {
        log("錯誤：語音辨識未授權（請至系統設定 > 隱私權 > 語音辨識 開啟）")
        try? logLines.joined(separator: "\n").write(toFile: logPath, atomically: true, encoding: .utf8)
        exit(1)
    }

    // --- 建立辨識器 ---
    guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "ja-JP")) else {
        log("錯誤：無法建立日文辨識器")
        try? logLines.joined(separator: "\n").write(toFile: logPath, atomically: true, encoding: .utf8)
        exit(1)
    }
    log("recognizer available: \(recognizer.isAvailable)")

    // --- 建立請求 ---
    let audioURL = URL(fileURLWithPath: audioPath)
    let request = SFSpeechURLRecognitionRequest(url: audioURL)
    request.shouldReportPartialResults = false
    request.taskHint = .dictation

    // --- 執行辨識，用 RunLoop 等待 ---
    var segments: [[String: Any]] = []
    var taskDone = false
    var taskError: String? = nil

    log("recognition task starting...")
    let task = recognizer.recognitionTask(with: request) { result, error in
        if let error = error {
            taskError = error.localizedDescription
            taskDone = true
            return
        }
        guard let result = result else { return }
        if result.isFinal {
            for seg in result.bestTranscription.segments {
                segments.append([
                    "text": seg.substring,
                    "start": seg.timestamp,
                    "duration": seg.duration,
                ])
            }
            taskDone = true
        }
    }

    // Spin RunLoop until done (max 120s)
    let deadline = Date().addingTimeInterval(120)
    while !taskDone && Date() < deadline {
        RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.1))
    }

    if !taskDone {
        log("警告：辨識超時（120s）")
        task.cancel()
    }

    if let err = taskError {
        log("辨識錯誤：\(err)")
    }
    log("segments_count:\(segments.count)")

    // --- 輸出 JSON ---
    do {
        let data = try JSONSerialization.data(withJSONObject: segments, options: .prettyPrinted)
        try data.write(to: URL(fileURLWithPath: outputPath))
        log("OK:\(segments.count)")
    } catch {
        log("JSON 寫入失敗：\(error)")
    }

    try? logLines.joined(separator: "\n").write(toFile: logPath, atomically: true, encoding: .utf8)
}

main()
