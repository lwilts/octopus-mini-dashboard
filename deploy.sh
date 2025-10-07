#!/bin/bash
# Quick deployment script for Octopus Agile Dashboard

set -e

echo "================================================"
echo "  Octopus Agile Dashboard - One-Click Deploy"
echo "================================================"
echo ""

# Check if ansible is installed
if ! command -v ansible-playbook &> /dev/null; then
    echo "Error: Ansible is not installed"
    echo "Install with: sudo dnf install ansible"
    exit 1
fi

# Check if Pi is reachable
echo "Checking connectivity to pizero.lab..."
if ansible pizero -m ping &> /dev/null; then
    echo "✓ Pi is reachable"
else
    echo "✗ Cannot reach pizero.lab"
    echo "  Make sure your Pi is powered on and network is configured"
    exit 1
fi

echo ""
echo "Starting deployment..."
echo ""

ansible-playbook deploy.yml

echo ""
echo "================================================"
echo "  Deployment Complete!"
echo "================================================"
echo ""
echo "Check status with:"
echo "  ansible pizero -m shell -a 'systemctl status agile-dashboard'"
echo ""
echo "View logs with:"
echo "  ansible pizero -m shell -a 'journalctl -u agile-dashboard -n 20'"
echo ""
