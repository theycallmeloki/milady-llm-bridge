#!/bin/bash

set -e

# Check if running on Windows
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
  echo "Windows detected. Please download the Windows binary directly from:"
  echo "https://github.com/theycallmeloki/mcp-llm-bridge/releases/latest"
  exit 1
fi

# Determine system
SYSTEM=$(uname -s | tr '[:upper:]' '[:lower:]')
if [[ "$SYSTEM" == "darwin" ]]; then
  SYSTEM="macos"
elif [[ "$SYSTEM" == "linux" ]]; then
  SYSTEM="linux"
else
  echo "Unsupported operating system: $SYSTEM"
  echo "Please download the appropriate binary directly from:"
  echo "https://github.com/theycallmeloki/milady-llm-bridge/releases/latest"
  exit 1
fi

# Determine architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "x86_64" ]]; then
  ARCH="amd64"
elif [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
  ARCH="arm64"
else
  echo "Unsupported architecture: $ARCH"
  echo "Please download the appropriate binary directly from:"
  echo "https://github.com/theycallmeloki/milady-llm-bridge/releases/latest"
  exit 1
fi

echo "Detected platform: $SYSTEM-$ARCH"

# Get latest release info
LATEST_RELEASE_URL=$(curl -s https://api.github.com/repos/theycallmeloki/milady-llm-bridge/releases/latest | grep "browser_download_url.*computer-$SYSTEM-$ARCH" | head -n 1 | sed 's/.*"browser_download_url": *"\(.*\)".*/\1/')

if [[ -z "$LATEST_RELEASE_URL" ]]; then
  echo "Error: Could not find a release for your platform ($SYSTEM-$ARCH)"
  echo "Please download the appropriate binary directly from:"
  echo "https://github.com/theycallmeloki/milady-llm-bridge/releases/latest"
  exit 1
fi

echo "Downloading latest computer CLI from: $LATEST_RELEASE_URL"

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
TEMP_FILE="$TEMP_DIR/computer"

# Download binary
curl -L -o "$TEMP_FILE" "$LATEST_RELEASE_URL"
chmod +x "$TEMP_FILE"

# Determine installation directory
PRIMARY_INSTALL_DIR="/usr/local/bin"
USER_BIN_DIR="$HOME/.local/bin"
FALLBACK_BIN_DIR="$HOME/bin"

if [ -w "$PRIMARY_INSTALL_DIR" ]; then
  # Can write to /usr/local/bin
  INSTALL_DIR="$PRIMARY_INSTALL_DIR"
  echo "Installing computer CLI to $INSTALL_DIR..."
  mv "$TEMP_FILE" "$INSTALL_DIR/computer"
elif command -v sudo >/dev/null 2>&1; then
  # Try with sudo
  INSTALL_DIR="$PRIMARY_INSTALL_DIR"
  echo "Installing computer CLI to $INSTALL_DIR (requires sudo)..."
  if sudo mv "$TEMP_FILE" "$INSTALL_DIR/computer" 2>/dev/null; then
    echo "Successfully installed with sudo."
  else
    # Fall back to user directory if sudo fails
    INSTALL_DIR="$USER_BIN_DIR"
    mkdir -p "$INSTALL_DIR"
    mv "$TEMP_FILE" "$INSTALL_DIR/computer"
    echo "Sudo failed. Installed to $INSTALL_DIR instead."
  fi
else
  # No sudo, use ~/.local/bin which is often in PATH
  INSTALL_DIR="$USER_BIN_DIR"
  mkdir -p "$INSTALL_DIR"
  mv "$TEMP_FILE" "$INSTALL_DIR/computer"
  echo "Installing computer CLI to $INSTALL_DIR (user directory)..."

  # Make sure the directory is in PATH
  if ! echo "$PATH" | grep -q "$INSTALL_DIR"; then
    echo "Adding $INSTALL_DIR to your PATH..."
    echo 'export PATH="$PATH:'"$INSTALL_DIR"'"' >> "$HOME/.bashrc"
    if [ -f "$HOME/.zshrc" ]; then
      echo 'export PATH="$PATH:'"$INSTALL_DIR"'"' >> "$HOME/.zshrc"
    fi
    echo "NOTE: You'll need to restart your terminal or run 'source ~/.bashrc' to use the computer command."
  fi
fi

# Clean up
rm -rf "$TEMP_DIR"

echo "✅ Installed computer CLI to $INSTALL_DIR/computer"

if echo "$PATH" | grep -q "$INSTALL_DIR"; then
  echo "You can now run the computer CLI by typing: computer"
else
  echo "To run the computer CLI, either:"
  echo "1. Restart your terminal session, or"
  echo "2. Run: source ~/.bashrc"
  echo "Then you can use the 'computer' command"
fi