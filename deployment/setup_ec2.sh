#!/usr/bin/env bash
# SignalShift AWS EC2 micro Automated Deployment Script ($0 Cost Setup)
# Domain Target: api.signalshift.subartaghosh.co.in
set -e

DOMAIN="api.signalshift.subartaghosh.co.in"

echo "========================================================="
echo "   SignalShift AWS EC2 micro Deployment Setup ($0 Budget)   "
echo "   Target Domain: ${DOMAIN}                             "
echo "========================================================="

# 1. Allocate 3GB Swap Memory to prevent RAM OOM crashes on 1GB t2.micro / t3.micro
echo "[1/6] Allocating 3GB Swap Memory..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 3G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=3072
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "✔ 3GB Swap configured successfully."
else
    echo "✔ Swap file already exists."
fi

# 2. System updates and package installations
echo "[2/6] Updating system packages..."
sudo apt update -y
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx git curl

# 3. Setup Python virtual environment & dependencies
echo "[3/6] Setting up Python virtual environment..."
cd "$(dirname "$0")/../backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm || true

# 4. Configure Systemd Service
echo "[4/6] Installing Systemd service..."
sudo cp "../deployment/signalshift-backend.service" /etc/systemd/system/signalshift-backend.service
sudo systemctl daemon-reload
sudo systemctl enable signalshift-backend
sudo systemctl restart signalshift-backend
echo "✔ Backend systemd service started."

# 5. Configure Nginx Reverse Proxy
echo "[5/6] Setting up Nginx reverse proxy..."
sudo cp "../deployment/nginx.conf" /etc/nginx/sites-available/signalshift
sudo ln -sf /etc/nginx/sites-available/signalshift /etc/nginx/sites-enabled/signalshift
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
echo "✔ Nginx reverse proxy configured for ${DOMAIN}."

# 6. Automatic SSL Certificate setup via Certbot
echo "[6/6] Setting up SSL Certificate via Certbot..."
if command -v certbot &> /dev/null; then
    sudo certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "contact@subartaghosh.co.in" || echo "⚠️ Certbot SSL skipped (Ensure DNS A Record points to EC2 IP first)."
fi

echo "========================================================="
echo "🎉 SignalShift EC2 Backend Deployment Complete!"
echo "Backend URL:   https://${DOMAIN}"
echo "Verify status: sudo systemctl status signalshift-backend"
echo "View logs:     sudo journalctl -u signalshift-backend -f"
echo "========================================================="
