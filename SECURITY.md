# Security Policy & Vulnerability Reporting

The Voice Bridge team takes the security of our real-time voice infrastructure, credentials, and desktop automation tools seriously.

---

## 1. Reporting a Vulnerability

If you discover a security vulnerability in Voice Bridge, please **do not open a public GitHub issue**. Instead, report it through one of the following responsible disclosure channels:

- **Private Security Advisory**: Open a Private Security Advisory via GitHub's "Security" tab.
- **Maintainer Email**: Contact the repository maintainers directly.

Please include:
1. Type of vulnerability (e.g., credential leakage, command injection, audio buffer overflow).
2. Step-by-step reproduction instructions or a minimal Proof-of-Concept (PoC).
3. Impact assessment on edge clients, backend containers, or cloud endpoints.

We aim to acknowledge receipt of vulnerability reports within **48 hours** and provide an estimated timeline for remediation.

---

## 2. Threat Model & Security Architecture

### 2.1 API Key Hygiene
- **Never commit `.env` to Git**: `.env` is explicitly ignored in [.gitignore](file:///c:/Users/ry729/arc-task-gen/.gitignore).
- **Server-Side Token Isolation**: Third-party API credentials (`RIME_API_KEY`, `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`) must **never** be bundled into frontend browser bundles. The browser client only calls the internal Express proxy (`POST /api/speak`).
- **LiveKit Secret Protection**: The `LIVEKIT_API_SECRET` must reside only on the FastAPI gateway (`server.py`) and LiveKit server containers. Native clients only receive signed, short-lived JWTs.

### 2.2 Desktop Automation Failsafes
- **PyAutoGUI Failsafe**: Enabled by default (`pyautogui.FAILSAFE = True`). Slamming the cursor to `(0, 0)` raises an immediate termination exception.
- **Application Whitelist**: The voice assistant restricts `launch_application` strictly to allowlisted system executables (`calc.exe`, `notepad.exe`, `mspaint.exe`, `explorer.exe`) and validated URL schemes (`http`, `https`, `mailto`). Arbitrary shell command execution via voice is rejected.
- **Input Character Limits**: Automated text typing is capped at 500 characters to prevent buffer overflow or denial-of-service.

### 2.3 Audio & Network Security
- **Local Audio Gating**: The local wake detector operates strictly on-device. Audio is neither buffered to persistent disk nor transmitted over the network until explicit wake detection occurs.
- **WebRTC Encryption**: LiveKit audio media is encrypted in transit using standard DTLS-SRTP protocols.
- **MQTT Isolation**: In production, the EMQX broker should enforce TLS (`8883`) and client certificate authentication or username/password access controls.
