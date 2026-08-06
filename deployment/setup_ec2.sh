#!/usr/bin/env bash
# SignalShift AWS EC2 Deployment Script
# Run from inside cloned repo: bash deployment/setup_ec2.sh
set -e

echo "========================================================="
echo "   SignalShift AWS EC2 micro Deployment Setup ($0 Budget)   "
echo "========================================================="

# 1. Allocate 3GB Swap Memory to prevent RAM OOM crashes on 1GB t2.micro / t3.micro
echo "[1/5] Allocating 3GB Swap Memory..."
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
echo "[2/5] Updating system packages..."
sudo apt update -y
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx git curl

# 3. Setup Python virtual environment & dependencies
echo "[3/5] Setting up Python virtual environment..."
cd "$(dirname "$0")/../backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install --no-cache-dir -r requirements.txt
pip cache purge || true
python -m spacy download en_core_web_sm || true

# 4. Configure Systemd Service
echo "[4/5] Installing Systemd service..."
sudo cp "../deployment/signalshift-backend.service" /etc/systemd/system/signalshift-backend.service
sudo systemctl daemon-reload
sudo systemctl enable signalshift-backend
sudo systemctl restart signalshift-backend
echo "✔ Backend systemd service started on port 8002."

# 5. Configure Nginx Reverse Proxy
echo "[5/5] Setting up Nginx reverse proxy..."
sudo cp "../deployment/nginx.conf" /etc/nginx/sites-available/signalshift
sudo ln -sf /etc/nginx/sites-available/signalshift /etc/nginx/sites-enabled/signalshift
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
echo "✔ Nginx reverse proxy configured for direct HTTP access."

PUBLIC_IP=$(curl -s ifconfig.me || echo "Your-EC2-Public-IP")

echo "========================================================="
echo "🎉 SignalShift EC2 Backend Deployment Complete!"
echo "Backend API URL: http://${PUBLIC_IP}"
echo "Verify health:   curl http://${PUBLIC_IP}/health"
echo "Verify status:   sudo systemctl status signalshift-backend"
echo "View logs:       sudo journalctl -u signalshift-backend -f"
echo "========================================================="
