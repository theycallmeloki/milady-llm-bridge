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
  echo "https://github.com/theycallmeloki/mcp-llm-bridge/releases/latest"
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
  echo "https://github.com/theycallmeloki/mcp-llm-bridge/releases/latest"
  exit 1
fi

echo "Detected platform: $SYSTEM-$ARCH"

# Get latest release info
LATEST_RELEASE_URL=$(curl -s https://api.github.com/repos/theycallmeloki/mcp-llm-bridge/releases/latest | grep "browser_download_url.*milady-$SYSTEM-$ARCH" | cut -d : -f 2,3 | tr -d \")

if [[ -z "$LATEST_RELEASE_URL" ]]; then
  echo "Error: Could not find a release for your platform ($SYSTEM-$ARCH)"
  exit 1
fi

echo "Downloading latest milady CLI from: $LATEST_RELEASE_URL"

# Fixed installation directory
INSTALL_DIR="/usr/local/bin"

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
TEMP_FILE="$TEMP_DIR/milady"

# Download binary
curl -L -o "$TEMP_FILE" "$LATEST_RELEASE_URL"
chmod +x "$TEMP_FILE"

# Check if sudo is needed
if [ -w "$INSTALL_DIR" ]; then
  echo "Installing milady CLI to $INSTALL_DIR..."
  mv "$TEMP_FILE" "$INSTALL_DIR/milady"
else
  echo "Installing milady CLI to $INSTALL_DIR (requires sudo)..."
  sudo mv "$TEMP_FILE" "$INSTALL_DIR/milady"
fi

# Clean up
rm -rf "$TEMP_DIR"

echo "✅ Installed milady CLI to $INSTALL_DIR/milady"
echo "You can now run the milady CLI by typing: milady"