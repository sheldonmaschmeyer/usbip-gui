FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies, including python3-tk for tkinter
# linux-tools-generic provides usbip on Ubuntu-based distributions
RUN apt-get update && apt-get install -y \
    linux-tools-generic \
    hwdata \
    python3 \
    python3-pip \
    python3-tk \
    sudo \
    zsh \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# The Ubuntu linux-tools wrapper at /usr/sbin/usbip expects the exact host kernel version.
# We bypass it by symlinking the actual installed binary directly to /usr/local/bin/usbip
RUN ln -sf $(ls -1 /usr/lib/linux-tools/*/usbip | head -n 1) /usr/local/bin/usbip

RUN sh -c "$(wget https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -O -)" --unattended && \
    cd ~/.oh-my-zsh/custom/plugins && \
    git clone https://github.com/zdharma-continuum/history-search-multi-word.git


# Set working directory
WORKDIR /app

# Install python dev tools
RUN pip3 install --no-cache-dir flake8 black pylint pytest

# Default command to run when the container starts
CMD ["/bin/zsh"]
