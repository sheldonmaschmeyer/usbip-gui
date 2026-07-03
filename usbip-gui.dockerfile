FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Define a default user home for COPY and other user-scoped operations
ARG USERNAME="ubuntu"
ARG USER_HOME="/home/$USERNAME"

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
    vim \
    kmod \
    udev \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Set locale for zsh agnoster theme characters
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# The Ubuntu linux-tools wrapper at /usr/sbin/usbip expects the exact host kernel version.
# We bypass it by symlinking the actual installed binary directly to /usr/local/bin/usbip
RUN ln -sf $(ls -1 /usr/lib/linux-tools/*/usbip | head -n 1) /usr/local/bin/usbip

# We allow non-root user to run sudo commands without a password prompt for
# convenience in the container. TODO: Consider removing this if possible.
RUN echo "${USERNAME} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/${USERNAME}

USER "${USERNAME}"

RUN sh -c "$(wget https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -O -)" --unattended && \
    cd ~/.oh-my-zsh/custom/plugins && \
    git clone https://github.com/zdharma-continuum/history-search-multi-word.git

COPY .zshrc "/home/${USERNAME}/.zshrc"

RUN wget -qO- https://pixi.sh/install.sh | zsh

ENV PATH="/home/${USERNAME}/.pixi/bin:$PATH"

# Set working directory
WORKDIR /home/${USERNAME}/usbip-gui

# Default command to run when the container starts
CMD ["pixi", "run", "usbip"]
