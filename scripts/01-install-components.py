def install_k3s(self) -> bool:
    """Install K3s with WSL2 dual-IP configuration."""
    if shutil.which("k3s"):
        self.log_message("K3s already installed", "SUCCESS")
        return True

    self.log_message("Installing K3s with WSL2 dual-IP configuration...")

    # Get both IPs for K3s configuration
    wsl2_ip = self._get_wsl2_ip()
    windows_host_ip = "192.168.0.50"

    # K3s installation with proper network binding for WSL2
    install_env = os.environ.copy()
    install_env.update({
        "INSTALL_K3S_EXEC": f"""--disable traefik --disable servicelb --disable local-storage \
        --write-kubeconfig-mode 644 \
        --bind-address {wsl2_ip} \
        --advertise-address {wsl2_ip} \
        --node-external-ip {windows_host_ip} \
        --flannel-iface eth0 \
        --node-ip {wsl2_ip}""",
        "K3S_KUBECONFIG_MODE": "644"
    })

    try:
        # Create K3s configuration directory
        os.makedirs("/etc/rancher/k3s", exist_ok=True)

        # Create K3s config file for WSL2
        k3s_config = f"""# K3s configuration for WSL2 dual-IP setup
bind-address: {wsl2_ip}
advertise-address: {wsl2_ip}
node-external-ip: {windows_host_ip}
node-ip: {wsl2_ip}
flannel-iface: eth0
disable:
  - traefik
  - servicelb
  - local-storage
write-kubeconfig-mode: "644"
cluster-init: true
"""

        with open("/tmp/k3s-config.yaml", "w") as f:
            f.write(k3s_config)

        # Install K3s with configuration
        result = subprocess.run(
            "curl -sfL https://get.k3s.io | sh -s - --config /tmp/k3s-config.yaml",
            shell=True,
            env=install_env,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            self.log_message("K3s installation completed", "SUCCESS")
        else:
            self.log_message(f"K3s installation failed: {result.stderr}", "ERROR")
            return False

    except Exception as e:
        self.log_message(f"K3s installation error: {e}", "ERROR")
        return False

    # Wait for K3s to start
    self.log_message("Waiting for K3s to start...")
    time.sleep(15)

    # Update K3s service for WSL2 (systemd may not work)
    self._setup_k3s_wsl2_service()

    # Setup kubeconfig with proper server endpoint
    return self._setup_k3s_kubeconfig(wsl2_ip, windows_host_ip)

def _get_wsl2_ip(self) -> str:
    """Get WSL2 instance IP address."""
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except:
        return "127.0.0.1"

def _setup_k3s_wsl2_service(self) -> None:
    """Setup K3s service for WSL2 environment."""
    try:
        # Check if systemd is available
        result = subprocess.run(["systemctl", "--version"], capture_output=True)
        if result.returncode == 0:
            # Systemd is available
            self.run_command(["sudo", "systemctl", "enable", "k3s"], "Enable K3s service")
            self.run_command(["sudo", "systemctl", "start", "k3s"], "Start K3s service")
        else:
            # No systemd, create init script
            self.log_message("Setting up K3s without systemd (WSL2 mode)", "INFO")
            init_script = """#!/bin/bash
# K3s startup script for WSL2
/usr/local/bin/k3s server --config /etc/rancher/k3s/config.yaml &
echo $! > /var/run/k3s.pid
"""
            with open("/tmp/k3s-start.sh", "w") as f:
                f.write(init_script)

            subprocess.run(["sudo", "chmod", "+x", "/tmp/k3s-start.sh"])
            subprocess.run(["sudo", "mv", "/tmp/k3s-start.sh", "/usr/local/bin/k3s-start.sh"])

            # Start K3s
            subprocess.run(["sudo", "/usr/local/bin/k3s-start.sh"])

    except Exception as e:
        self.log_message(f"K3s service setup warning: {e}", "WARNING")

def _setup_k3s_kubeconfig(self, wsl2_ip: str, windows_host_ip: str) -> bool:
    """Setup kubeconfig for dual-IP access."""
    try:
        # Create .kube directory
        kube_dir = Path.home() / ".kube"
        kube_dir.mkdir(exist_ok=True)

        # Copy K3s kubeconfig
        subprocess.run([
            "sudo", "cp", "/etc/rancher/k3s/k3s.yaml",
            str(kube_dir / "config")
        ])

        # Update ownership
        subprocess.run([
            "sudo", "chown", f"{os.getenv('USER')}:{os.getenv('USER')}",
            str(kube_dir / "config")
        ])

        # Update kubeconfig server URL for external access
        kubeconfig_path = kube_dir / "config"
        with open(kubeconfig_path, "r") as f:
            content = f.read()

        # Replace localhost with WSL2 IP for internal access
        content = content.replace("https://127.0.0.1:6443", f"https://{wsl2_ip}:6443")

        with open(kubeconfig_path, "w") as f:
            f.write(content)

        # Create additional kubeconfig for external access (agent node)
        external_config = content.replace(f"https://{wsl2_ip}:6443", f"https://{windows_host_ip}:6443")

        with open(kube_dir / "config-external", "w") as f:
            f.write(external_config)

        self.log_message("Kubeconfig configured for dual-IP access", "SUCCESS")

        # Test kubectl access
        success, output = self.run_command(["kubectl", "get", "nodes"], "kubectl cluster access test")
        if success:
            self.installed_components.append(f"K3s cluster: {output.strip().split()[0]} node ready")
            self.log_message(f"✅ K3s accessible on WSL2 IP: {wsl2_ip}:6443", "SUCCESS")
            self.log_message(f"✅ K3s accessible on Windows IP: {windows_host_ip}:6443", "SUCCESS")
            return True
        else:
            self.log_message("kubectl access test failed", "ERROR")
            return False

    except Exception as e:
        self.log_message(f"Kubeconfig setup failed: {e}", "ERROR")
        return False
