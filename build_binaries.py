#!/usr/bin/env python3
"""
Build script to create standalone binaries for mcp-llm-bridge using PyInstaller.
This script supports building for multiple platforms using Docker.
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
    if system == "darwin":
        system = "macos"
        
    machine = platform.machine().lower()
    if machine == "x86_64":
        machine = "amd64"
    elif machine in ["aarch64", "arm64"]:
        machine = "arm64"
    
    # Create dist directory
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    # Set binary name based on platform
    binary_name = f"computer-{system}-{machine}"
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

def build_docker(platform, arch):
    """Build for the specified platform and architecture using Docker"""
    if platform == "macos":
        docker_platform = f"linux/{arch}"
        print(f"Note: Building macOS binaries requires a macOS host. Using Linux/{arch} as fallback.")
        platform = "linux"
    elif platform == "windows" and arch == "arm64":
        print("Note: Windows ARM64 is not fully supported. Building for Windows AMD64 instead.")
        docker_platform = "linux/amd64"
        arch = "amd64"
    else:
        docker_platform = f"linux/{arch}"
    
    binary_name = f"computer-{platform}-{arch}"
    if platform == "windows":
        binary_name += ".exe"
    
    print(f"Building for {platform}-{arch} using Docker on {docker_platform}")
    
    # Get current directory as absolute path
    current_dir = os.path.abspath(os.getcwd())
    
    # Create dist directory
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    # Prepare Docker build command
    docker_cmd = [
        "docker", "run", "--platform", docker_platform, "--rm",
        "-v", f"{current_dir}:/app", "-w", "/app",
        "python:3.12-slim",
        "bash", "-c",
        "apt-get update && "
        "apt-get install -y python3-pip && "
        "pip install pyinstaller && "
        "pip install -e . && "
        f"pyinstaller --onefile --name {binary_name} src/mcp_llm_bridge/main.py && "
        f"chmod 755 dist/{binary_name}"
    ]
    
    # Run Docker command
    try:
        run_command(docker_cmd)
        print(f"Build complete. Binary available at dist/{binary_name}")
    except subprocess.CalledProcessError as e:
        print(f"Error building {platform}-{arch} binary: {e}")
        print("Make sure Docker is installed and has proper architecture emulation support.")
        print("For ARM64 emulation: docker run --privileged --rm tonistiigi/binfmt --install arm64")

def build_linux_arm64():
    """Legacy function for backward compatibility"""
    build_docker("linux", "arm64")

def build_all():
    """Build binaries for all supported platforms"""
    platforms = [
        ("linux", "amd64"),
        ("linux", "arm64"),
        ("windows", "amd64"),
    ]
    
    for platform, arch in platforms:
        try:
            print(f"\n=== Building {platform}-{arch} ===\n")
            build_docker(platform, arch)
        except Exception as e:
            print(f"Error building {platform}-{arch}: {e}")
    
    print("\nBuild process complete. Check the dist/ directory for binaries.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build mcp-llm-bridge binaries")
    parser.add_argument("--platform", 
                        choices=["native", "linux-amd64", "linux-arm64", "windows-amd64", "all", "arm64"],
                        default="native", 
                        help="Target platform (default: native)")
    
    args = parser.parse_args()
    
    if args.platform == "native":
        build_native()
    elif args.platform == "arm64" or args.platform == "linux-arm64":
        build_linux_arm64()
    elif args.platform == "linux-amd64":
        build_docker("linux", "amd64")
    elif args.platform == "windows-amd64":
        build_docker("windows", "amd64")
    elif args.platform == "all":
        build_all()