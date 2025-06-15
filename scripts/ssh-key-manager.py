class WSL2SSHKeyManager:
    """SSH key manager for WSL2 with Windows host integration."""

    def __init__(self):
        self.console = Console()
        self.log_file = Path("logs/ssh-setup.log")
        self.log_file.parent.mkdir(exist_ok=True)

        # Find Windows SSH keys
        self.windows_ssh_path = self._find_windows_ssh_keys()
        self.wsl2_ssh_path = Path.home() / ".ssh"

    def _find_windows_ssh_keys(self) -> Optional[Path]:
        """Locate Windows SSH keys accessible from WSL2."""
        try:
            # Get Windows username
            result = subprocess.run(
                ["powershell.exe", "-Command", "$env:USERNAME"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                windows_user = result.stdout.strip()
                windows_ssh_path = Path(f"/mnt/c/Users/{windows_user}/.ssh")

                if windows_ssh_path.exists():
                    self.log_message(f"Found Windows SSH directory: {windows_ssh_path}")
                    return windows_ssh_path

            # Fallback locations
            fallback_paths = [
                Path("/mnt/c/Users/Administrator/.ssh"),
                Path(f"/mnt/c/Users/{os.getenv('USER', 'ubuntu')}/.ssh"),
            ]

            for path in fallback_paths:
                if path.exists():
                    return path

        except Exception as e:
            self.log_message(f"Error finding Windows SSH keys: {e}", "WARNING")

        return None

    def setup_ssh_keys(self) -> bool:
        """Setup SSH keys for WSL2 environment."""
        self.log_message("Setting up SSH keys for WSL2...")

        # Create WSL2 SSH directory
        self.wsl2_ssh_path.mkdir(mode=0o700, exist_ok=True)

        if self.windows_ssh_path and (self.windows_ssh_path / "id_rsa").exists():
            # Use existing Windows SSH keys
            return self._link_windows_ssh_keys()
        else:
            # Generate new SSH keys
            return self._generate_new_ssh_keys()

    def _link_windows_ssh_keys(self) -> bool:
        """Link Windows SSH keys to WSL2."""
        try:
            # Copy Windows SSH keys to WSL2
            for key_file in ["id_rsa", "id_rsa.pub"]:
                windows_key = self.windows_ssh_path / key_file
                wsl2_key = self.wsl2_ssh_path / key_file

                if windows_key.exists():
                    shutil.copy2(windows_key, wsl2_key)
                    # Set proper permissions
                    if key_file == "id_rsa":
                        wsl2_key.chmod(0o600)
                    else:
                        wsl2_key.chmod(0o644)

                    self.log_message(f"Copied {key_file} from Windows to WSL2")

            # Test SSH key
            return self._test_ssh_key()

        except Exception as e:
            self.log_message(f"Failed to link Windows SSH keys: {e}", "ERROR")
            return False

    def _generate_new_ssh_keys(self) -> bool:
        """Generate new SSH keys for WSL2."""
        try:
            key_path = self.wsl2_ssh_path / "id_rsa"

            # Generate SSH key pair
            result = subprocess.run([
                "ssh-keygen",
                "-t", "rsa",
                "-b", "4096",
                "-f", str(key_path),
                "-N", "",  # No passphrase
                "-C", "wsl2-homelab@192.168.0.51"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self.log_message("Generated new SSH key pair for WSL2")

                # Copy to Windows SSH directory if it exists
                if self.windows_ssh_path:
                    try:
                        for key_file in ["id_rsa", "id_rsa.pub"]:
                            shutil.copy2(
                                self.wsl2_ssh_path / key_file,
                                self.windows_ssh_path / key_file
                            )
                        self.log_message("Synchronized SSH keys with Windows")
                    except Exception as e:
                        self.log_message(f"Warning: Could not sync to Windows: {e}", "WARNING")

                return self._test_ssh_key()
            else:
                self.log_message(f"SSH key generation failed: {result.stderr}", "ERROR")
                return False

        except Exception as e:
            self.log_message(f"SSH key generation error: {e}", "ERROR")
            return False

    def _test_ssh_key(self) -> bool:
        """Test SSH key functionality."""
        try:
            # Test key format
            result = subprocess.run([
                "ssh-keygen", "-l", "-f", str(self.wsl2_ssh_path / "id_rsa.pub")
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self.log_message(f"SSH key validation: {result.stdout.strip()}")
                return True
            else:
                self.log_message("SSH key validation failed", "ERROR")
                return False

        except Exception as e:
            self.log_message(f"SSH key test error: {e}", "ERROR")
            return False

    def setup_agent_node_access(self, agent_ip: str = "192.168.0.66") -> bool:
        """Setup SSH access to agent node."""
        self.log_message(f"Setting up SSH access to agent node: {agent_ip}")

        try:
            # Test current SSH access
            result = subprocess.run([
                "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                f"ubuntu@{agent_ip}", "echo 'SSH test successful'"
            ], capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                self.log_message("SSH access to agent node already working", "SUCCESS")
                return True
            else:
                self.log_message("SSH access to agent node needs setup", "WARNING")
                return self._setup_ssh_copy_id(agent_ip)

        except Exception as e:
            self.log_message(f"SSH test to agent node failed: {e}", "ERROR")
            return False

    def _setup_ssh_copy_id(self, agent_ip: str) -> bool:
        """Setup SSH key-based auth to agent node."""
        try:
            # Interactive password prompt for initial setup
            password = self.console.input(f"[yellow]Enter password for ubuntu@{agent_ip}: [/yellow]", password=True)

            # Use ssh-copy-id with sshpass
            result = subprocess.run([
                "sshpass", "-p", password,
                "ssh-copy-id", "-o", "StrictHostKeyChecking=no",
                f"ubuntu@{agent_ip}"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self.log_message("SSH key copied to agent node successfully", "SUCCESS")
                return True
            else:
                self.log_message(f"SSH key copy failed: {result.stderr}", "ERROR")
                return False

        except Exception as e:
            self.log_message(f"SSH setup error: {e}", "ERROR")
            return False
