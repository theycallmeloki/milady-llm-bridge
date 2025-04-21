#!/usr/bin/env python3
"""
Build script to create standalone binaries for mcp-llm-bridge using PyInstaller.
This script supports building for the current platform or cross-compiling using Docker.
"""

import os
import platform
import subprocess
import sys
import shutil
import argparse
from pathlib import Path

def run_command(cmd):
    print(f"Running: {' '.join(cmd if isinstance(cmd, list) else cmd.split())}")
    subprocess.run(cmd if isinstance(cmd, list) else cmd.split(), check=True)

def build_native():
    """Build for the current platform"""
    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        run_command([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Get platform info
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if machine == "x86_64":
        machine = "amd64"
    elif machine in ["aarch64", "arm64"]:
        machine = "arm64"
    
    # Create dist directory
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    # Set binary name based on platform
    binary_name = f"milady-{system}-{machine}"
    if system == "windows":
        binary_name += ".exe"
    
    # PyInstaller command
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--name", binary_name,
        "src/mcp_llm_bridge/main.py"
    ]
    
    # Run PyInstaller
    run_command(pyinstaller_cmd)
    
    # Clean up build files
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    if os.path.exists(f"{binary_name}.spec"):
        os.remove(f"{binary_name}.spec")
    
    print(f"Build complete. Binary available at dist/{binary_name}")

def build_docker_arm64():
    """Build for Linux ARM64 using Docker"""
    print("Building for Linux ARM64 using Docker")
    
    # Get current directory as absolute path
    current_dir = os.path.abspath(os.getcwd())
    
    # Prepare Docker build command
    docker_cmd = [
        "docker", "run", "--platform", "linux/arm64", "--rm",
        "-v", f"{current_dir}:/app", "-w", "/app",
        "python:3.12-slim",
        "bash", "-c",
        "apt-get update && "
        "apt-get install -y python3-pip && "
        "pip install pyinstaller && "
        "pip install -e . && "
        "pyinstaller --onefile --name milady-linux-arm64 src/mcp_llm_bridge/main.py && "
        "chmod 755 dist/milady-linux-arm64"
    ]
    
    # Create dist directory
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    # Run Docker command
    try:
        run_command(docker_cmd)
        print("Build complete. Binary available at dist/milady-linux-arm64")
    except subprocess.CalledProcessError as e:
        print(f"Error building ARM64 binary: {e}")
        print("Make sure Docker is installed and has ARM64 emulation support.")
        print("You may need to run: docker run --privileged --rm tonistiigi/binfmt --install arm64")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build mcp-llm-bridge binaries")
    parser.add_argument("--platform", choices=["native", "arm64"], 
                        default="native", help="Target platform (default: native)")
    
    args = parser.parse_args()
    
    if args.platform == "native":
        build_native()
    elif args.platform == "arm64":
        build_docker_arm64()