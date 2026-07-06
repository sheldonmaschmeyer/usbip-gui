# usbip-gui

This is a fork of K-Francis-H's `usbip-gui`, created to integrate SSL/SSH
encryption directly into the graphical interface. While `usbip` can currently be
tunnelled securely via SSH from the command line, this fork aims to make secure
USB sharing over the internet as fast and seamless as commercial alternatives
like USB Network Gate (eveusb).

USB Network Gate offers a cross-platform GUI (Windows and Mac) and relies on its
own proprietary kernel module rather than `usbip`. This is a useful workaround
for devices like the Jetson Xavier where `usbip` modules aren't installed by
default. However, its reliance on unstable cumbersome recurring license key
checks makes it unreliable. Since `usbip` is fully open-source and free of
licensing restrictions, this fork seeks to provide a simplified, faster, and
more dependable secure USB sharing experience.

## Docker

I prefer using Docker rather than integrating directly onto the host system to
keep the environment completely isolated. This avoids installing system-wide
dependencies on your machine (like `python3-tkinter`, `meson`, etc.). Because
Docker provides a consistent, reproducible, and clean environment without
complex setup steps, it is ideal for both development and production.

To open an interactive shell inside the Docker container:

```zsh
docker compose -f ./docker-compose.yml run usbip-gui /bin/zsh
```

Once inside the container, you can run the application using `pixi`:

```zsh
pixi run usbip
```

Alternatively, to start the application directly without an interactive shell, use:

```zsh
docker compose -f ./docker-compose.yml up usbip-gui
```

## Translations

If you make changes to the English or French translations in the `.po` files
(`po/en.po` or `po/fr_CA.po`), you will need to compile them into `.mo` files
for the changes to take effect in the application.

Run the following commands from the root directory to compile the `.po` files
into the `share/locale` directory:

```zsh
mkdir -p share/locale/en/LC_MESSAGES share/locale/fr_CA/LC_MESSAGES
msgfmt po/en.po -o share/locale/en/LC_MESSAGES/usbip-gui.mo
msgfmt po/fr_CA.po -o share/locale/fr_CA/LC_MESSAGES/usbip-gui.mo
```

## Secure Connection (SSL Tunneling)

This fork introduces a seamlessly integrated SSL proxy mechanism to encrypt
`usbip` traffic over the internet using self-signed certificates and a custom
pre-shared password. `usbip` normally transmits data over unencrypted TCP, which
is highly insecure on public networks.

### How it works
**Note:** Port 3240 used in explanations but, you may use a custom port.
When the **Secure** checkbox is enabled, the application spawns an isolated
Python-based SSL tunneling script (`ssl_tunnel.py`):
1. **On the Server (Host):** The tunnel dynamically generates a temporary
   self-signed RSA certificate and binds to the default `usbip` port (`3240`).
   The actual `usbipd` service is re-assigned to listen on an internal-only port
   (`13240`).
2. **On the Client:** A background client proxy binds to a random local port
   (e.g. `45864`) and initiates a secure SSL connection to the server on port
   `3240`. `usbip` commands on the client (like `list` and `attach`) are
   transparently forwarded to this local proxy.
3. **Authentication:** The server verifies the pre-shared password before
   allowing any traffic to reach the underlying `usbipd` daemon.

### Connecting over the Internet

To securely share a USB device across the internet:
1. **Port Forwarding:** You only need to open and port-forward TCP port
   **`3240`** on the Server's router. You do **not** need to open port `13240`.
2. **Start the Server:** In the GUI's "Server" tab, check the **Secure** box,
   enter a secure password, and click **Restart Server**.
3. **Connect the Client:** In the GUI's "Client" tab, enter the Server's public
   IP address or hostname in the **Host** field. Leave the **Port** as `3240`.
4. Check the **Secure** box and enter the exact same password you set on the
   server.
5. Click **Refresh Remote** or **Attach** to seamlessly connect over the
   encrypted tunnel!

## Tasks

- [x] Dockerize and configure a comfortable coding environment.
- [x] Apply types and linting rules, reviewing the code thoroughly before adding
  new features.
- [x] reducing/eliminating global variable usage
- [x] Add SSL/SSH encryption feature.
- [ ] Move code into modules, i.e. compartmentalize sections of the guy.py.
- [ ] Cross-architecture (ARM and x86) production testing.
- [ ] Look at K-Francis-H's remaining TODOs.

## Screenshot

![screenshot of usbip gui_v1_en](screenshots/usbip_gui_v1_en.png)
Figure 1: USBIP GUI v1 English screenshot

![screenshot of usbip gui_v1_fr](screenshots/usbip_gui_v1_fr.png)
Figure 2: USBIP GUI v1 French screenshot

## References
[Original K-Francis-H's README](https://github.com/K-Francis-H/usbip-gui/blob/main/README.md)

