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

## Tasks

- [x] Dockerize and configure a comfortable coding environment.
- [x] Apply types and linting rules, reviewing the code thoroughly before adding
  new features.
- [] Add SSL/SSH encryption feature.
- [] Cross-architecture (ARM and x86) production testing.
- [] Look at K-Francis-H's TODOs including reducing/eliminating global variable
  usage and moving code into modules.

# Original K-Francis-H's README

An attempt at wrapping the usbip linux kernel module with a gui for easier
usability/configurability

## Dependencies

This project only runs on Linux, you will need to install `linux-tools-generic`
to get the usbip kernel module. Installation should look something like this:

**deb-based:**

```bash
sudo apt install linux-tools-generic

sudo modprobe usbip_host
sudo modprobe usbip_core
sudo modprobe vhci_hcd

#then to start the gui use either of

sudo python3 gui.py

#or

python3 main.py

#which uses gksudo to start the gui
```

You may also have problems getting `tkinter.ttk` to import correctly. This
script assumes that you are using Python 3.8+ so make sure thats the version
that you are using.

## Development

### Requirements

- `python`
- `python3-tkinter`
- `usbip`
- `meson`

### Build

```bash
meson setup .build/
meson compile -C .build/
```

## Screenshot

![screenshot of usbip gui](screenshots/usbip_gui.png)
