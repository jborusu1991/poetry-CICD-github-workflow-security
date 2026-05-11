<h1>This Projects shows how an end to end github actions workflow file looks like for a Poetry project:</h1>

The pipeliene includes building, testing, Semgrep(SAST, SCA,Secret Scanning) , trivy(container scanning), Dependency Track for sbom

🚀 1. Overview

This workflow implements a full CI/CD + DevSecOps pipeline for a Python project using:<br>

🐍 Poetry (dependency management)<br>
🧪 Pytest (testing)<br>
🧬 MyPy (type checking)<br>
🔍 Semgrep (SAST security scanning)<br>
🐳 Docker (container build)<br>
☁️ AWS ECR (container registry)<br>
🛡️ Trivy (container vulnerability scanning + SBOM)<br>
📦 Dependency Track (SBOM ingestion)<br>

⚙️ 2. Triggers<br>
on:<br>
  push:<br>
    branches: [feat/**, main, master]<br>

  pull_request:<br>
    branches: [main, master]<br>
Behaviour:<br>
Event	Action<br>
Feature branch push	Full CI pipeline<br>
PR to main/master	CI + security checks<br>
Main push	Full CI + build + scan + publish<br>

3. Permissions
permissions:<br>
  contents: read<br>
  security-events: write<br>
  packages: write<br>
  id-token: write<br>

Purpose:<br>
Permission	Usage<br>
contents	checkout code<br>
security-events	SARIF/security results<br>
packages	container/package publishing<br>
id-token	AWS OIDC authentication  <br>

4. Concurrency Control<br>
concurrency:<br>
  group: ecr-ci-${{ github.ref }}<br>
  cancel-in-progress: true<br>
Purpose:<br>
Prevents duplicate builds for same branch<br>
Cancels older pipeline runs automatically<br>
Ensures only latest commit is deployed<br>

5. Global Environment Variables<br>
Variable	Purpose<br>
PYTHON_VERSION	Python runtime version<br>
AWS_REGION	AWS deployment region<br>
ECR_REGISTRY	Docker registry URL<br>
ECR_REPOSITORY	ECR repo name<br>
TRIVY_REPORT_*	SBOM output config<br>

6. Job Architecture<br>
typing → tests → semgrep → build-image → publish → trivy → dependency-track<br>

🧪 7. Jobs Breakdown<br>
🧬 7.1 Typing (MyPy)<br>
Purpose:<br>

Static type checking<br>

Features:<br>
Python 3.12 container<br>
pip configured with internal Nexus registry<br>
Poetry caching enabled<br>
certificate injection<br>
Output:<br>
type validation (non-blocking)<br>

🧪 7.2 Tests (Pytest)<br>
Purpose:<br>

Unit + coverage testing<br>

Output:<br>
HTML coverage report<br>
XML coverage report<br>
JUnit test results artifact<br>

🔍 7.3 Semgrep (SAST, SCA,Secret Security Scans)<br>
Purpose:<br>

Static security analysis<br>

Features:<br>
Runs inside Semgrep container<br>
Branch-aware scanning<br>
Cached rules for speed<br>
Output:<br>
security scan results available on semgrep appsec platform<br>

🐳 7.4 Build Image (Docker + AWS ECR)<br>
Depends on:<br>
semgrep<br>
Responsibilities:<br>
Builds Docker image<br>
Tags image using commit SHA<br>
Pushes to AWS ECR<br>
Uses BuildKit caching (gha cache)<br>
Multi-arch build (amd64 + arm64)<br>
Authentication:<br>
AWS OIDC role assumption (no static keys)<br>

📦 7.5 Publish Python Package<br>
Runs only on:<br>
main branch<br>
Actions:<br>
builds Python package via Poetry<br>
publishes to private Nexus repo<br>

📊 7.7 Dependency Track<br>
Depends on:<br>
trivy<br>
Purpose:<br>

Uploads SBOM to Dependency Track server<br>

API call:<br>
uploads BOM file<br>
associates with project + branch/version<br>

🔐 8. Security Gates<br>
Enforced checks:<br>
--------------------------------
Tool	|       Rule<br>
-------------------------------
Semgrep	     code vulnerabilities<br>
Trivy	     HIGH + CRITICAL block<br>
Dependency 	 SBOM validation<br>
Track<br>

⚡ 9. Build Optimization<br>
Enabled features:<br>
multi-stage caching (cache-from/cache-to)<br>
dependency caching<br>
parallel jobs (typing, tests, semgrep)<br>
concurrency cancellation<br>
Docker multi stage builds<br>

☁️ 10. AWS Integration<br>
Authentication:<br>
OIDC (id-token: write)<br>
No static AWS keys used<br>
Flow:<br>
GitHub → Assume AWS Role → Push to ECR<br>

🚦 11. Pipeline Flow Diagram<br>
push/PR<br>
   ↓
typing ─────┐<br>
             ↓<br>
tests ────── semgrep<br>
             ↓<br>
         build-image<br>
             ↓<br>
           publish<br>
             ↓<br>
            trivy<br>
             ↓<br>
     dependency-track<br>


🧩 12. Key Design Principles<br>
✔ Shift-left security<br>
Semgrep runs before build<br>
✔ Immutable builds<br>
Docker tagged with commit SHA<br>
✔ Supply chain security<br>
SBOM generation + tracking<br>
✔ Fast CI<br>
caching everywhere<br>
concurrency cancellation<br>
✔ Cloud-native auth<br>
AWS OIDC (no secrets)<br>

