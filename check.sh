#!/bin/bash
# Pre-deployment checks for Octopus Agile Dashboard

echo "Running pre-deployment checks..."
echo ""

# Check Ansible syntax
echo "1. Checking Ansible playbook syntax..."
ansible-playbook deploy.yml --syntax-check
if [ $? -eq 0 ]; then
    echo "   ✓ Playbook syntax is valid"
else
    echo "   ✗ Playbook syntax check failed"
    exit 1
fi

echo ""

# Check if templates exist
echo "2. Checking template files..."
for template in templates/dashboard.py.j2 templates/dashboard.service.j2; do
    if [ -f "$template" ]; then
        echo "   ✓ $template exists"
    else
        echo "   ✗ $template missing"
        exit 1
    fi
done

echo ""

# Check if variables are defined
echo "3. Checking configuration..."
if [ -f "group_vars/all.yml" ]; then
    echo "   ✓ group_vars/all.yml exists"

    # Check key variables
    for var in octopus_region agile_product gas_product; do
        if grep -q "$var:" group_vars/all.yml; then
            echo "   ✓ $var is defined"
        else
            echo "   ✗ $var is not defined"
            exit 1
        fi
    done
else
    echo "   ✗ group_vars/all.yml missing"
    exit 1
fi

echo ""

# Check inventory
echo "4. Checking inventory..."
if [ -f "inventory.ini" ]; then
    echo "   ✓ inventory.ini exists"
    if grep -q "pizero.lab" inventory.ini; then
        echo "   ✓ pizero host is defined"
    else
        echo "   ! Warning: pizero.lab not found in inventory"
    fi
else
    echo "   ✗ inventory.ini missing"
    exit 1
fi

echo ""
echo "================================================"
echo "All checks passed! Ready to deploy."
echo "================================================"
echo ""
echo "Run: ./deploy.sh"
echo ""
