# Terms and Conditions of Use

*Last Updated: September 2026*

Please read these Terms and Conditions ("Terms", "Agreement") carefully before installing, deploying, or utilizing the **Voice Bridge & Ambient IoT Voice Platform** (the "Software", "Platform", or "Service").

By accessing, running, building, or contributing to this repository, you agree to be bound by these Terms. If you disagree with any part of these Terms, you may not use the Software.

---

## 1. Scope of the Software & Intended Use

1.1 **Prototype & Operational Assistant**: Voice Bridge is an engineering prototype and extensible platform designed for voice-native incident handoffs, desktop accessibility, and smart IoT device management.

1.2 **Human-in-the-Loop Requirement**: While Voice Bridge extracts structured incident data from spoken language and synthesizes spoken briefings, it is **not** a substitute for certified emergency dispatch, life-safety telemetry systems, or licensed human operator judgment. All critical operational decisions must be verified by qualified personnel.

---

## 2. Voice Data, Audio Buffering & Privacy Policy

2.1 **Local Wake-Word Processing**:
- The Software utilizes open-source on-device wake-word detection (`openWakeWord`, `Porcupine`).
- In its dormant state ("SLEEPING"), ambient microphone audio is processed strictly within a local, volatile, in-memory circular PCM buffer.
- **No idle ambient audio is transmitted over the network or saved to disk while the system is sleeping.**

2.2 **Third-Party Cloud Processing**:
- Once a wake word or recording trigger occurs, audio data, transcripts, and operational prompts are sent to external third-party API providers according to your configuration:
  - **Rime Labs Inc.**: For text-to-speech voice generation.
  - **OpenAI LLC**: For language understanding, function calling, and conversation logic.
  - **Deepgram Inc.**: For streaming speech-to-text transcription.
- By configuring API keys for these providers, you acknowledge and agree that your audio and text prompts are subject to their respective privacy policies and data retention agreements.

2.3 **No Biometric Identification**: The Software does not harvest or persist biometric voiceprints for the purpose of personal user identification without explicit configuration.

---

## 3. Acceptable Use Policy

You agree **NOT** to use the Software:
1. To violate any applicable local, state, national, or international law or regulation.
2. In safety-critical environments where software failure could lead directly to death, personal injury, severe physical or environmental damage (e.g., nuclear facilities, aircraft navigation, life-support systems).
3. To execute unauthorized automated actions, keylogging, or desktop control on computers without the explicit permission of the device owner.
4. To synthesize deceptive, non-consensual voice deepfakes or impersonate individuals with malicious intent.
5. To generate harassing, defamatory, abusive, or unlawful content.

---

## 4. Desktop Automation & Safety Failsafes

4.1 **Operating System Control**: The Windows Voice Controller and Alexa Backend utilize automation tools (`pyautogui`, `pycaw`) capable of executing keystrokes, mouse events, and launching programs.

4.2 **Safety Failsafe Acknowledgment**: You acknowledge that moving the mouse cursor into any corner of the screen triggers the PyAutoGUI `FailSafeException`, immediately aborting active automated routines. Users must not disable this failsafe in production or unattended environments.

4.3 **User Responsibility**: You assume total responsibility for commands vocalized to the system. The authors and contributors are not liable for accidental data loss, application closure, or system modifications resulting from voice commands.

---

## 5. Third-Party Services & Open Source Dependencies

5.1 The Software integrates with multiple independent third-party services and open-source packages:
- **DuckDuckGo (`ddgs`)**: Public web search queries.
- **Open-Meteo**: Weather forecast API.
- **LiveKit**: WebRTC media streaming.
- **EMQX**: Distributed MQTT message broker.

5.2 The platform authors make no warranties regarding the uptime, availability, accuracy, or continuous operation of third-party APIs.

---

## 6. Disclaimer of Warranties

THE SOFTWARE IS PROVIDED **"AS IS"** AND **"AS AVAILABLE"**, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, ACCURACY, AND NON-INFRINGEMENT.

IN NO EVENT SHALL THE AUTHORS, COPYRIGHT HOLDERS, OR CONTRIBUTORS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT (INCLUDING NEGLIGENCE), OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## 7. Modifications & Termination

We reserve the right to modify or replace these Terms at any time. Your continued use of the Software following any changes constitutes acceptance of the new Terms.

---

## 8. Contact & Inquiries

For questions regarding these Terms or operational compliance, please open an issue or pull request in the official project repository.
