# Homelab Installation Guide

## Installation Process

1. **Prerequisites Setup:**

   ```bash
   # Install UV package manager if not already installed
   pip install uv

   # Initialize UV and create virtual environment
   uv init
   uv venv .venv

   # Activate the virtual environment
   # On Linux/WSL2:
   source .venv/bin/activate
   # On Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # On Windows Command Prompt:
   .venv\Scripts\activate.bat
   ```

2. **Run System Audit:**

   ```bash
   make audit
   # or
   python3 scripts/00-system-audit.py   ```

3. **Install All Components:**

   ```bash
   make install
   # or
   python3 scripts/01-install-components.py
   ```

4. **Update PATH and Verify:**

   ```bash
   source ~/.bashrc
   make verify
   ```

5. **Complete Process:**

   ```bash
   make all  # Runs audit, install, and verify
   ```

## Additional Utility Commands

1. **Health Monitoring:**

   ```bash
   make health-check    # Comprehensive cluster health check
   make monitor         # Start continuous monitoring
   make status          # Show comprehensive system status
   ```

2. **Discovery and Optimization:**

   ```bash
   make discover        # Discover smart home devices on network
   make optimize        # Analyze and optimize system performance
   ```

3. **Backup and Updates:**

   ```bash
   make backup          # Create full system backup
   make update-all      # Safely update all components
   ```

4. **Development Workflow:**

   ```bash
   make dev-setup       # Setup optimal development environment
   make dev-reset       # Reset development environment (requires UV initialization first)
   make quick-test      # Quick smoke tests

   # Manual environment setup
   uv init              # Initialize UV package manager
   uv venv .venv        # Create virtual environment
   source .venv/bin/activate  # Activate environment (Linux/WSL2)
   # or
   .venv\Scripts\activate     # Activate environment (Windows)
   ```

5. **Emergency Operations:**

   ```bash
   make disaster-recovery  # Show disaster recovery options
   ```

## Key Features

- **Interactive audit** with system requirements checking
- **Modular installation** with individual component validation
- **Comprehensive logging** with timestamped entries and external log files
- **Error handling** with rollback suggestions and troubleshooting guidance
- **K3s without Traefik** properly configured for container-based Traefik deployment
- **WSL2 optimization** with proper networking and systemd configuration
- **Success reporting** with detailed installation summary and next steps
- **Continuous monitoring** with health checks and performance optimization
- **Smart home device discovery** with automatic configuration generation
- **Backup management** with full system backup capabilities
- **Development environment** with automated setup and testing

The scripts handle WSL2-specific configurations, provide extensive error handling, and generate comprehensive logs for troubleshooting. Each component is installed with proper verification and the system is configured to work seamlessly with the future agent node integration.

---

## Potential Installation Pitfalls and Mitigation Strategies

### WSL2-Specific Pitfalls

### **Systemd Not Enabled**

**Problem:** K3s requires systemd for service management, but WSL2 doesn't enable it by default.

- **Symptoms:** K3s installation fails with "systemctl not found" or service start failures
- **Mitigation:** Script automatically checks and enables systemd in `/etc/wsl.conf`, then prompts for WSL restart

### **Windows Path Interference**

**Problem:** Windows PATH variables can interfere with Linux binaries in WSL2.

- **Symptoms:** Wrong version of tools being executed, or Windows executables being called instead of Linux ones
- **Mitigation:** Scripts explicitly use full paths and update `.bashrc` with proper PATH ordering

### **Memory and Resource Constraints**

**Problem:** WSL2 default memory limits may be insufficient for K3s cluster.

- **Symptoms:** K3s pods failing to start, out-of-memory errors during installation
- **Mitigation:** Script checks available resources and warns if below 4GB RAM/20GB disk minimums

## Network Configuration Pitfalls

### **IP Address Mismatch**

**Problem:** Expected control node IP (192.168.0.50) doesn't match actual WSL2 networking.

- **Symptoms:** K3s API server inaccessible from other nodes, networking failures
- **Mitigation:** Audit script validates IP configuration and warns about mismatches

### **Port Conflicts**

**Problem:** Required ports (6443, 80, 443) already in use by Windows services or Docker Desktop.

- **Symptoms:** K3s installation fails, services can't bind to ports
- **Mitigation:** Script checks port availability and identifies conflicting processes

### **DNS Resolution Issues**

**Problem:** WSL2 DNS configuration conflicts with corporate networks or VPNs.

- **Symptoms:** Package downloads fail, connectivity issues to external repositories
- **Mitigation:** Script tests internet connectivity and provides fallback DNS configurations

## Package Management Pitfalls

### **Dependency Conflicts**

**Problem:** Ubuntu package conflicts between system packages and manually installed tools.

- **Symptoms:** Installation failures, version conflicts, broken dependencies
- **Mitigation:** Scripts use isolated installation methods (pip --user, direct downloads) where possible

### **Repository Access Issues**

**Problem:** Corporate firewalls or proxy settings blocking package downloads.

- **Symptoms:** apt update failures, curl/wget timeouts, GPG key retrieval failures
- **Mitigation:** Script includes offline installation options and proxy detection

### **Insufficient Disk Space**

**Problem:** WSL2 virtual disk runs out of space during installation.

- **Symptoms:** Package installation failures, "No space left on device" errors
- **Mitigation:** Pre-installation audit checks available space and provides cleanup suggestions

## K3s-Specific Pitfalls

### **Traefik Conflict**

**Problem:** K3s installs Traefik by default, conflicting with planned container-based Traefik deployment.

- **Symptoms:** Port 80/443 conflicts, ingress controller issues
- **Mitigation:** Installation script explicitly uses `--disable traefik` flag

### **Kubeconfig Permission Issues**

**Problem:** K3s kubeconfig file has restrictive permissions preventing regular user access.

- **Symptoms:** kubectl commands fail with permission denied errors
- **Mitigation:** Script copies kubeconfig to user directory with proper ownership

### **Service Start Failures**

**Problem:** K3s service fails to start due to systemd issues or resource constraints.

- **Symptoms:** K3s installation completes but cluster is not accessible
- **Mitigation:** Script includes service verification steps and troubleshooting guidance

## Docker Integration Pitfalls

### **Docker Desktop Conflicts**

**Problem:** Docker Desktop for Windows conflicts with WSL2 Docker installation.

- **Symptoms:** Container runtime errors, socket permission issues
- **Mitigation:** Script detects existing Docker installations and provides configuration guidance

### **Container Runtime Issues**

**Problem:** K3s container runtime conflicts with Docker daemon.

- **Symptoms:** Pods fail to start, containerd errors
- **Mitigation:** Proper K3s configuration to use containerd without Docker conflicts

## SSH and Authentication Pitfalls

### **SSH Key Generation Failures**

**Problem:** SSH key generation fails due to entropy issues or permission problems.

- **Symptoms:** SSH key setup script fails, passwordless authentication doesn't work
- **Mitigation:** Script includes multiple key generation methods and entropy checking

### **Agent Node Connectivity**

**Problem:** Control node cannot reach agent node (192.168.0.66) for cluster setup.

- **Symptoms:** K3s agent registration fails, node not joining cluster
- **Mitigation:** Network connectivity validation and troubleshooting guidance

## Python Environment Pitfalls

### **UV Package Manager Not Initialized**

**Problem:** UV package manager not properly initialized before running installation scripts that depend on it.

- **Symptoms:** Commands like `uv sync --all-extras` fail with "project not initialized" errors, virtual environment not found
- **Mitigation:** Installation guide includes explicit prerequisite steps for UV initialization (`uv init` and `uv venv .venv`) before running any scripts

### **Package Version Conflicts**

**Problem:** System Python packages conflict with user-installed packages.

- **Symptoms:** Import errors, version compatibility issues
- **Mitigation:** Scripts use virtual environments and --user installations

### **Missing System Dependencies**

**Problem:** Python packages require system libraries not installed by default.

- **Symptoms:** Compilation errors during pip installations
- **Mitigation:** Script installs essential build tools and development headers

## Post-Installation Pitfalls

### **Service Discovery Issues**

**Problem:** K3s cluster services not properly registering or discovering each other.

- **Symptoms:** Applications can't connect to databases, networking issues
- **Mitigation:** Comprehensive verification scripts test service connectivity

### **Resource Exhaustion**

**Problem:** Initial cluster setup consumes all available resources.

- **Symptoms:** System becomes unresponsive, services crash
- **Mitigation:** Resource monitoring and limits configuration

### **Log Rotation Issues**

**Problem:** Verbose logging fills up disk space rapidly.

- **Symptoms:** System crashes due to full disk, log files consuming all space
- **Mitigation:** Proper log rotation configuration and monitoring

## Recovery Strategies

### **Rollback Procedures**

- **Automated cleanup:** Scripts include rollback functions for failed installations
- **State preservation:** System state captured before major changes
- **Service restoration:** Ability to restore previous working configurations

### **Troubleshooting Tools**

- **Diagnostic scripts:** Automated problem detection and resolution suggestions
- **Log analysis:** Structured logging with error categorization
- **Health checks:** Comprehensive system and service validation

### **Manual Intervention Points**

- **Interactive prompts:** User confirmation for potentially destructive operations
- **Skip options:** Ability to skip failed components and continue
- **Debug modes:** Verbose logging and step-by-step execution options

## Prevention Best Practices

### **Pre-Installation Validation**

- System requirements checking before starting installation
- Network connectivity and configuration validation
- Resource availability assessment

### **Modular Installation**

- Independent component installation with individual validation
- Ability to retry failed components without full reinstallation
- Clear dependency management and ordering

### **Comprehensive Logging**

- Detailed logging of all operations with timestamps
- Error categorization and suggested remediation steps
- Success/failure tracking with rollback information

The installation scripts are designed with these pitfalls in mind, implementing defensive programming practices, comprehensive error handling, and detailed logging to minimize the risk of installation failures and provide clear guidance when issues occur.
