# Contributing to Voice Bridge

Thank you for your interest in contributing to the **Voice Bridge & Ambient IoT Voice Platform**! This document outlines our code standards, branching workflows, and pull request guidelines.

---

## 1. Code of Conduct

All contributors and maintainers are expected to uphold a welcoming, professional, and harassment-free community standard. Treat all participants with respect and constructive feedback.

---

## 2. Development Workflow

1. **Fork & Branch**:
   - Fork the repository on GitHub.
   - Create a dedicated feature branch from `main`:
     ```bash
     git checkout -b feature/my-new-feature
     ```

2. **Environment Setup**:
   - Install Node.js dependencies:
     ```bash
     npm install
     ```
   - Install Python dependencies:
     ```powershell
     py -m pip install -r requirements.txt
     py -m pip install -r clients/windows/requirements.txt
     ```

3. **Writing Code & Conventions**:
   - **TypeScript / Frontend**: Use strict type definitions. Do not use `any` unless absolutely required for external library interop.
   - **Python**: Follow PEP 8 guidelines. Include type hints (`mypy` compliant) on all function arguments and returns.
   - **Audio Safety**: Never alter ring buffer thread synchronization without adding corresponding unit tests in `clients/windows/test_preroll.py`.

---

## 3. Running Verification Tests

Before committing code or opening a PR, ensure all tests and linters pass:

```powershell
# 1. Run circular ring buffer unit tests
py clients/windows/test_preroll.py

# 2. Typecheck TypeScript
npx tsc --noEmit

# 3. Verify Express health probe
Invoke-RestMethod -Uri http://localhost:8787/api/health
```

---

## 4. Pull Request Checklist

When submitting a Pull Request, ensure:
- [ ] PR title is concise and descriptive (e.g., `feat(tts): add fallback for Rime WebSocket timeout`).
- [ ] Any new environment variables are documented in [.env.example](file:///c:/Users/ry729/arc-task-gen/.env.example) and [docs/API_REFERENCE.md](file:///c:/Users/ry729/arc-task-gen/docs/API_REFERENCE.md).
- [ ] No hardcoded API keys or personal access tokens are included in commits.
- [ ] Documentation has been updated for any new endpoints, tools, or architectural changes.
