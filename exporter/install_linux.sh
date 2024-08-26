#!/bin/bash

# Function to ask for input
ask() {
    local prompt="$1"
    local default="$2"
    read -p "$prompt [$default]: " input
    echo "${input:-$default}"
}

# Function to check if a string is a valid URL
is_valid_url() {
    local url=$1
    if [[ $url =~ ^(http|https):\/\/[a-zA-Z0-9.-]+(:[0-9]+)?(\/.*)?$ ]]; then
        return 0
    else
        return 1
    fi
}

# Check the operating system and version
os_check() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        if [[ "$ID" == "ubuntu" && "${VERSION_ID%.*}" -ge 22 ]]; then
            return 0
        elif [[ "$ID" == "debian" && "${VERSION_ID%.*}" -ge 12 ]]; then
            return 0
        fi
    fi
    return 1
}

# Validate the OS version
validate_os() {
    if ! os_check; then
        echo "Error: This script requires Ubuntu 22.04 or higher, Debian 12 or higher"
        exit 1
    fi
}

# Validate URLs
validate_urls() {
    if ! is_valid_url "$prometheus_url"; then
        echo "Error: The Prometheus URL '$prometheus_url' is not valid."
        exit 1
    fi
}

# Install TIG exporter
install_tig_exporter() {
    echo "Creating necessary directory structure..."
    mkdir -p ~/tig_exporter
    cd ~/tig_exporter

    echo "Downloading the TIG exporter script and requirements..."
    wget https://raw.githubusercontent.com/fpatron/tig-dashboard/master/exporter/tig_exporter.py -O tig_exporter.py
    wget https://raw.githubusercontent.com/fpatron/tig-dashboard/master/exporter/requirements.txt -O requirements.txt

    echo "Installing Python3, pip, and virtualenv..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-virtualenv

    echo "Setting up a virtual environment..."
    virtualenv venv

    echo "Installing required Python packages..."
    venv/bin/pip install -r requirements.txt

    # Updating python script
    if [ ! -z "$1" ]
    then
        sed -i "s|PLAYER_IDS = \[\]|PLAYER_IDS = $1|g" tig_exporter.py
    fi
    if [ ! -z "$2" ]
    then
        sed -i "s|INNOVATOR_IDS = \[\]|INNOVATOR_IDS = $2|g" tig_exporter.py
    fi
}

# Install TIG service
install_tig_service() {
    # Create the systemd service file
    username=$(whoami)
    exporter_path=$(pwd)

    echo "Creating systemd service file for TIG exporter..."
    sudo bash -c "cat <<EOL > /lib/systemd/system/tig_exporter.service
[Unit]
Description=TIG Exporter Service
After=network.target
[Service]
User=$username
Group=$username
WorkingDirectory=$exporter_path
ExecStart=$exporter_path/venv/bin/python $exporter_path/tig_exporter.py
Restart=always
[Install]
WantedBy=multi-user.target
EOL"

    echo "Enabling systemd daemon..."
    sudo systemctl daemon-reload
    sudo systemctl enable tig_exporter
    sudo systemctl start tig_exporter
}

# Install Grafana Alloy
install_grafana_alloy() {
    echo "Installing Grafana Alloy..."
    sudo mkdir -p /etc/apt/keyrings/
    wget -q -O - https://apt.grafana.com/gpg.key | gpg --dearmor | sudo tee /etc/apt/keyrings/grafana.gpg > /dev/null
    echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
    sudo apt update
    sudo apt-get install alloy -y
}

# Configure Grafana Alloy
configure_grafana_alloy() {
    echo "Configuring Grafana Alloy..."
    sudo mkdir -p /etc/alloy
    wget https://raw.githubusercontent.com/fpatron/tig-dashboard/master/alloy/config.alloy -O /tmp/config.alloy

    # Replace variables in the config file
    sed -i "s|<PROMETHEUS_ENDPOINT>|$1|g" /tmp/config.alloy
    sed -i "s|<PROMETHEUS_USERNAME>|$2|g" /tmp/config.alloy
    sed -i "s|<PROMETHEUS_PASSWORD>|$3|g" /tmp/config.alloy

    sudo mv /tmp/config.alloy /etc/alloy/config.alloy

    # Restart Alloy service
    echo "Restarting Grafana Alloy service..."
    sudo systemctl daemon-reload
    sudo systemctl restart alloy
}

display_logo() {
    clear
    echo "TIG Dashboard installation"
    echo "
███████████████████████████████████████
███████████████████████████████████████
███████████████████████████████████████
███████████████████████████████████████
███████████████████████████████████████
            ███████████████
            ███████████████
            ███████████████
            ███████████████
            ███████████████
            ███████████████
            ███████████████
            ███████████████
            ███████████████
            ███████████████
            ███████████████
            ███████████████
"
}


# Main script
main() {
    # Display Q logo
    display_logo

    # Validate OS
    validate_os

    # Ask for input
    player_ids=$(ask "What are your player addresses? (can be empty)" "ex: [\"0x73C7A2e1C9eb014EDbad892487D4cd4FEc5B239f\",\"0x73C7A2e1C9eb014EDbad892487D4cd4FEc5B239f\"]")
    innovator_ids=$(ask "What are your innovator addresses? (can be empty)" "ex: [\"0x73C7A2e1C9eb014EDbad892487D4cd4FEc5B239f\",\"0x73C7A2e1C9eb014EDbad892487D4cd4FEc5B239f\"]")

    prometheus_url=$(ask "Please enter the Prometheus URL" "ex: http://X.X.X.X:9090/api/v1/write")
    prometheus_user=$(ask "Please enter the Prometheus user (optional)" "")
    prometheus_api_key=$(ask "Please enter the Prometheus password (optional)" "")

    validate_urls

    # Print out the collected information
    echo "TIG player addresses: $player_ids"
    echo "TIG innovator addresses: $innovator_ids"
    echo "Prometheus URL: $prometheus_url"
    echo "Prometheus user: $prometheus_user"
    echo "Prometheus password: $prometheus_api_key"

    # Install TIG exporter
    install_tig_exporter $player_ids $innovator_ids
    install_tig_service

    # Install Grafana Alloy
    install_grafana_alloy

    # Configure Grafana Alloy
    configure_grafana_alloy $prometheus_url $prometheus_user $prometheus_api_key

    echo "Installation and setup completed successfully."
}

# Run the main function
main
