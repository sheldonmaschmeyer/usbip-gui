# Security Policy

Thank you for helping to keep USB/IP Manager secure. I, Sheldon, take the security of this project, including its secure features, seriously. This document outlines our policy for reporting and handling security vulnerabilities.

## Supported Versions

I actively support and provide security updates for the latest version of the application.

## In-Scope Vulnerabilities

I are particularly interested in addressing security vulnerabilities related to:
* **SSL/SSH Tunneling Bypasses:** Weaknesses or flaws in security (`ssl_tunnel.py`) that allow bypassing encryption.
* **Authentication Bypasses:** Issues that allow clients to attach or list shared USB devices without providing the correct pre-shared key/password.
* **Remote Code Execution (RCE):** Vulnerabilities that allow executing arbitrary commands on the server or client machine via the GUI or proxy.
* **Privilege Escalation:** Flaws in how setup scripts (e.g. `setup_usbip.sh`) or GUI helper commands execute with root permissions (`sudo`).
* **Information Disclosure:** Unintended leakage of private keys, certificates, passwords, or system information in logs, console outputs, or UI.

## Reporting a Vulnerability

**Please do not open public GitHub Issues or Pull Requests for security vulnerabilities.**

To report a vulnerability, please use one of the following methods:

### 1. GitHub Private Vulnerability Reporting (Preferred)
If you found a security bug, please report it privately via GitHub:
1. Navigate to the repository page on GitHub.
2. Click on the **Security** tab.
3. Under **Vulnerability reporting**, click **Report a vulnerability**.
4. Fill out the details of the issue and submit. This allows us to collaborate on a fix in a secure, private environment.

### 2. Request a Private Discussion (Alternative)
If Private Vulnerability Reporting is not enabled or available for this repository:
1. Navigate to the **Issues** or **Discussions** tab.
2. Open a new issue or discussion with a generic title (e.g., "Request to report security vulnerability privately").
3. **Do not include any vulnerability details, steps to reproduce, or code** in the public thread.
4. The repository maintainers will respond with contact instructions where you can share and discuss the details securely.

## Our Commitment

Upon receiving a valid vulnerability report, I commit to the following timeline and actions:
1. **Acknowledgment:** I will acknowledge receipt of your report.
2. **Investigation:** I will investigate the issue, determine its severity, and keep you updated on our progress.
3. **Fixing:** I will develop a fix in a private branch/security fork.
4. **Disclosure:** Once the patch is released, I will publish a Security Advisory to credit your contribution (unless you prefer to remain anonymous).

## Disclosure Policy

I follow a coordinated vulnerability disclosure process. I ask that you give us a reasonable window, I am an individual working on this project, to address the issue before disclosing it publicly.
