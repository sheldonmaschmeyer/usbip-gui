#!/bin/bash
set -e

echo "Loading kernel modules..."
sudo modprobe usbip_core
sudo modprobe usbip_host
sudo modprobe vhci_hcd

echo "Starting udev daemon (required for usbip port/attach to find vhci_hcd)..."
sudo /lib/systemd/systemd-udevd --daemon
sudo udevadm trigger

echo "Checking if usbipd is running..."
if ! pgrep -x "usbipd" > /dev/null; then
    echo "Starting usbipd in daemon mode..."
    sudo usbipd -D
else
    echo "usbipd is already running."
fi

echo "Environment is ready!"
