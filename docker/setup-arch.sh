#!/usr/bin/env bash
# Helper script to install & enable Docker on Arch Linux for ApplyPilot
set -e

echo "=== ApplyPilot Docker Setup for Arch Linux ==="

# Check if Docker is already installed
if command -v docker &> /dev/null; then
    echo "✔ Docker is already installed: $(docker --version)"
else
    echo "Installing docker and docker-compose via pacman..."
    sudo pacman -S --needed docker docker-compose
fi

# Enable and start Docker daemon
echo "Enabling and starting Docker service..."
sudo systemctl enable --now docker

# Add current user to docker group if not already added
if groups "$USER" | grep &>/dev/null '\bdocker\b'; then
    echo "✔ User '$USER' is already in the 'docker' group."
else
    echo "Adding user '$USER' to the 'docker' group..."
    sudo usermod -aG docker "$USER"
    echo "✔ Added '$USER' to 'docker' group."
    echo "NOTE: You may need to log out and back in (or run 'newgrp docker') for group changes to take effect."
fi

# Verify status
echo "Checking Docker service status..."
sudo systemctl is-active --quiet docker && echo "✔ Docker service is ACTIVE." || echo "✖ Docker service is NOT active."

echo "=== Setup complete! ==="
echo "You can now run: docker compose build"
