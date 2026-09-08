import AVFoundation
import AudioToolbox
import Foundation
import LiveKit
import Porcupine

@MainActor
final class VoiceOrchestrator: NSObject, ObservableObject {
    private var porcupine: PorcupineManager?
    private var room: Room?
    private var sessionTask: Task<Void, Never>?
    private let apiBaseURL: URL
    private let picovoiceAccessKey: String
    private let userID: String

    init(apiBaseURL: URL, picovoiceAccessKey: String, userID: String) {
        self.apiBaseURL = apiBaseURL
        self.picovoiceAccessKey = picovoiceAccessKey
        self.userID = userID
    }

    func start() {
        do {
            porcupine = try PorcupineManager(
                accessKey: picovoiceAccessKey,
                keyword: .computer,
                onDetection: { [weak self] _ in
                    Task { @MainActor in await self?.handleWakeWord() }
                }
            )
            try porcupine?.start()
        } catch {
            print("Wake-word startup failed: \(error)")
        }
    }

    func stop() {
        sessionTask?.cancel()
        porcupine?.stop()
        porcupine = nil
        Task { await room?.disconnect() }
        room = nil
    }

    private func handleWakeWord() async {
        porcupine?.stop()
        porcupine = nil
        playChime()

        // Porcupine and WebRTC both own AVAudioSession. Give iOS one run-loop turn
        // to release the local detector before WebRTC activates the microphone.
        try? await Task.sleep(for: .milliseconds(75))
        sessionTask = Task { [weak self] in
            guard let self else { return }
            do {
                let session = try await fetchSession()
                let audioSession = AudioManager.shared.audioSession
                try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .defaultToSpeaker])
                try audioSession.setActive(true)
                let newRoom = Room()
                try await newRoom.connect(url: session.wsURL, token: session.token)
                room = newRoom
                try await newRoom.localParticipant.setMicrophone(enabled: true)

                // Observe agent completion or inactivity in the app delegate and call resetToSleeping().
                try? await Task.sleep(for: .seconds(60))
                await resetToSleeping()
            } catch {
                print("Voice session failed: \(error)")
                await resetToSleeping()
            }
        }
    }

    func resetToSleeping() async {
        try? await room?.localParticipant.setMicrophone(enabled: false)
        await room?.disconnect()
        room = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        start()
    }

    private func playChime() {
        AudioServicesPlaySystemSound(1057)
    }

    private struct SessionResponse: Decodable {
        let token: String
        let wsUrl: String
        var wsURL: URL { URL(string: wsUrl)! }
    }

    private func fetchSession() async throws -> SessionResponse {
        let url = apiBaseURL.appendingPathComponent("api/v1/session/token")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: [
            "user_id": userID,
            "room_name": "iot-control-room"
        ])
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(SessionResponse.self, from: data)
    }
}
