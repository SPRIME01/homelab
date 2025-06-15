class SystemAuditor:
    def __init__(self):
        self.console = Console()
        self.required_ports = [6443, 80, 443, 8080, 9090, 3000]
        self.log_file = Path("logs/system-audit.log")
        self.log_file.parent.mkdir(exist_ok=True)

        # WSL2-specific configuration
        self.windows_host_ip = "192.168.0.50"
        self.wsl2_expected_ip = "192.168.0.51"
        self.windows_ssh_path = self._find_windows_ssh_path()

    def _find_windows_ssh_path(self) -> Optional[Path]:
        """Find Windows SSH keys accessible from WSL2."""
        possible_paths = [
            Path("/mnt/c/Users") / os.getenv("USER", "ubuntu") / ".ssh",
            Path("/mnt/c/Users") / "Administrator" / ".ssh",
        ]

        # Try to find actual Windows username
        try:
            result = subprocess.run(
                ["cmd.exe", "/c", "echo %USERNAME%"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                windows_user = result.stdout.strip()
                possible_paths.insert(0, Path("/mnt/c/Users") / windows_user / ".ssh")
        except:
            pass

        for path in possible_paths:
            if path.exists() and (path / "id_rsa").exists():
                self.log_message(f"Found Windows SSH keys at: {path}")
                return path

        self.log_message("No Windows SSH keys found", "WARNING")
        return None

    def check_wsl2_networking(self) -> Dict:
        """Check WSL2 networking configuration with dual IP setup."""
        network_info = {
            "wsl2_ip": None,
            "windows_host_ip": self.windows_host_ip,
            "expected_wsl2_ip": self.wsl2_expected_ip,
            "ip_match": False,
            "windows_host_reachable": False,
            "agent_node_reachable": False,
            "internet_connectivity": False,
            "ssh_keys_accessible": False
        }

        try:
            # Get WSL2 IP address
            hostname = socket.gethostname()
            wsl2_ip = socket.gethostbyname(hostname)
            network_info["wsl2_ip"] = wsl2_ip

            # Check if WSL2 IP matches expected
            if wsl2_ip == self.wsl2_expected_ip:
                network_info["ip_match"] = True
                self.log_message(f"✅ WSL2 IP matches expected: {wsl2_ip}")
            else:
                self.log_message(f"⚠️ WSL2 IP mismatch. Expected: {self.wsl2_expected_ip}, Got: {wsl2_ip}", "WARNING")

            # Test connectivity to Windows host
            try:
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "2", self.windows_host_ip],
                    capture_output=True,
                    timeout=5
                )
                network_info["windows_host_reachable"] = result.returncode == 0
                status = "✅" if result.returncode == 0 else "❌"
                self.log_message(f"{status} Windows host ({self.windows_host_ip}) reachability")
            except:
                self.log_message("❌ Cannot test Windows host connectivity", "WARNING")

            # Test connectivity to agent node
            try:
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "2", "192.168.0.66"],
                    capture_output=True,
                    timeout=5
                )
                network_info["agent_node_reachable"] = result.returncode == 0
                status = "✅" if result.returncode == 0 else "❌"
                self.log_message(f"{status} Agent node (192.168.0.66) reachability")
            except:
                self.log_message("❌ Cannot test agent node connectivity", "WARNING")

            # Check SSH key accessibility
            if self.windows_ssh_path:
                network_info["ssh_keys_accessible"] = True
                self.log_message("✅ Windows SSH keys accessible from WSL2")

            # Test internet connectivity
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=5)
                network_info["internet_connectivity"] = True
                self.log_message("✅ Internet connectivity verified")
            except:
                self.log_message("❌ No internet connectivity", "WARNING")

        except Exception as e:
            self.log_message(f"Network check failed: {e}", "ERROR")

        return network_info

    def display_wsl2_network_info(self, network_info: Dict) -> None:
        """Display WSL2-specific network information."""
        network_table = Table(title="WSL2 Network Configuration")
        network_table.add_column("Component", style="cyan")
        network_table.add_column("Value", style="green")
        network_table.add_column("Status", style="yellow")

        network_table.add_row(
            "Windows Host IP",
            network_info["windows_host_ip"],
            "✅ Expected" if network_info["windows_host_reachable"] else "❌ Unreachable"
        )
        network_table.add_row(
            "WSL2 Instance IP",
            network_info.get("wsl2_ip", "Unknown"),
            "✅ Expected" if network_info["ip_match"] else "⚠️ Different"
        )
        network_table.add_row(
            "Agent Node",
            "192.168.0.66",
            "✅ Reachable" if network_info["agent_node_reachable"] else "❌ Unreachable"
        )
        network_table.add_row(
            "Windows SSH Keys",
            str(self.windows_ssh_path) if self.windows_ssh_path else "Not Found",
            "✅ Accessible" if network_info["ssh_keys_accessible"] else "❌ Not Found"
        )

        self.console.print(network_table)
