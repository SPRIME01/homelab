# 🏠 Smart Home K3s Lab

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![UV](https://img.shields.io/badge/UV-package%20manager-green.svg)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A comprehensive infrastructure automation and monitoring solution for modern homelab environments, featuring K3s Kubernetes clusters, Supabase backend services, and intelligent system orchestration.

## ✨ Features

### 🚀 **Infrastructure as Code**

- **Pulumi-based** Kubernetes deployment automation
- **Supabase** complete stack deployment (PostgreSQL, PostgREST, GoTrue, Realtime, Storage, Kong)
- **K3s** lightweight Kubernetes cluster management
- **WSL2/Jetson** optimized for hybrid development environments

### 🔧 **Development Excellence**

- **UV package manager** for blazing-fast dependency management
- **Modern Python** with strict typing (mypy) and automated formatting (ruff)
- **CLI-first** approach with rich terminal interfaces
- **Pre-commit hooks** and automated code quality checks

### 📊 **Monitoring & Observability**

- **System health monitoring** with automated diagnostics
- **Network topology discovery** and validation
- **Performance optimization** tools and metrics
- **Disaster recovery** planning and backup automation

### 🔐 **Security & Best Practices**

- **Environment-based** secret management
- **Role-based access control** (RBAC) for Kubernetes
- **Automated security audits** and compliance checks
- **SSH key management** across hybrid environments

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **UV package manager** (automatically installed if missing)
- **WSL2** (for Windows users) or **Linux environment**
- **Git** for version control

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd homelab

# Run the complete setup (UV will be installed automatically)
make all
```

The setup process will:

1. 🔍 **Audit** your system configuration
2. ⚙️ **Install** all required components
3. ✅ **Verify** the installation

### Alternative Installation Methods

<details>
<summary>Manual UV Installation</summary>

```bash
# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync --all-extras

# Run system audit
uv run python scripts/00-system-audit.py

# Install components
uv run python scripts/01-install-components.py
```

</details>

<details>
<summary>Development Setup</summary>

```bash
# Install development dependencies
make dev-install

# Set up pre-commit hooks
uv run pre-commit install

# Run tests
make test

# Start development environment
make dev-setup
```

</details>

## 🎯 Usage

### Command Line Interface

The homelab CLI provides comprehensive management capabilities:

```bash
# Show system status
homelab status

# Run health checks
homelab health-check

# Discover network topology
homelab discover

# Backup system configuration
homelab backup

# Optimize performance
homelab optimize

# Monitor system metrics
homelab monitor
```

### Infrastructure Deployment

Deploy Supabase infrastructure to your K3s cluster:

```bash
# Deploy complete Supabase stack
uv run python -m infrastructure.supabase

# Configure environment variables first (recommended)
export SUPABASE_POSTGRES_PASSWORD="your-secure-password"
export SUPABASE_JWT_SECRET="your-32-character-jwt-secret"
export KUBECONFIG="~/.kube/config"
```

### System Management

Common administrative tasks:

```bash
# System audit and diagnostics
make audit

# Update all components
make update-all

# Clean development artifacts
make clean

# Reset development environment
make dev-reset
```

## 📁 Project Structure

```
homelab/
├── 📄 README.md                 # Project documentation
├── ⚙️ pyproject.toml           # Python project configuration
├── 🔧 Makefile                 # Build and automation scripts
├── 📋 LICENSE                  # MIT license
├── 🔒 .env                     # Environment variables (not tracked)
│
├── 📁 src/                     # Source code
│   ├── homelab/                # Main application package
│   │   ├── cli/               # Command-line interface
│   │   └── services/          # Core service modules
│   └── cli/                   # Additional CLI tools
│
├── 🧱 infrastructure/          # Infrastructure as Code
│   ├── supabase.py            # Supabase deployment (Pulumi)
│   └── supabase_config.py     # Configuration templates
│
├── 📝 scripts/                # Automation scripts
│   ├── 00-system-audit.py     # System diagnostics
│   ├── 01-install-components.py # Component installation
│   ├── backup-manager.py      # Backup automation
│   ├── cluster-health-monitor.py # Health monitoring
│   └── performance-optimizer.py # Performance tuning
│
├── 🧪 tests/                  # Comprehensive Test Suite (90%+ Coverage)
│   ├── unit/                  # Unit tests for individual components
│   │   ├── test_uv_utils.py
│   │   ├── test_system_audit.py
│   │   ├── test_ssh_key_manager.py
│   │   ├── test_install_components.py
│   │   ├── test_supabase_infrastructure.py
│   │   └── test_cli_main.py
│   ├── integration/           # Integration and end-to-end tests
│   │   ├── test_component_interactions.py
│   │   ├── test_component_contracts.py
│   │   ├── test_configuration_validation.py
│   │   └── test_end_to_end_workflows.py
│   ├── makefile/             # Makefile target testing
│   │   ├── test_makefile_targets.py
│   │   └── test_makefile_comprehensive.py
│   ├── fixtures/             # Test data and mocks
│   │   └── test_data.py
│   ├── test_helpers.py       # Testing utilities and AAA base classes
│   ├── conftest.py          # Pytest configuration and fixtures
│   └── test_supabase.py     # Legacy infrastructure tests
│
├── 📚 docs/                   # Documentation
│   ├── planning/              # Architecture and design docs
│   ├── SUPABASE_MIGRATION.md  # Migration guides
│   └── *.md                   # Additional documentation
│
├── 🔧 ansible/                # Ansible playbooks (planned)
├── 🐳 docker-compose.dev.yml  # Development containers
└── 📋 .github/                # GitHub Actions workflows
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file for your environment:

```bash
# Kubernetes Configuration
KUBECONFIG=~/.kube/config

# Supabase Configuration
SUPABASE_POSTGRES_PASSWORD=your-secure-password
SUPABASE_JWT_SECRET=your-32-character-jwt-secret
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Network Configuration (WSL2 specific)
WINDOWS_HOST_IP=192.168.0.50
WSL2_IP=192.168.0.51

# Development Settings
LOG_LEVEL=INFO
DEBUG=false
```

### Custom Configuration

The project supports flexible configuration through:

- 📄 **YAML configuration files** for service settings
- 🔧 **Python configuration classes** for type-safe settings
- 🌍 **Environment variable overrides** for deployment-specific values
- 📝 **Makefile variables** for build customization

## 🧪 Testing

### Comprehensive Test Suite (90%+ Coverage)

This project includes a robust testing framework with unit, integration, and Makefile testing:

```bash
# Run complete test suite with coverage
make test

# Run specific test categories
uv run pytest tests/unit/ -v               # Unit tests
uv run pytest tests/integration/ -v        # Integration tests
uv run pytest tests/makefile/ -v           # Makefile tests
uv run pytest tests/ --cov=src --cov=scripts --cov=infrastructure  # Coverage

# Generate coverage reports
uv run python scripts/coverage_analysis.py --generate-report
make coverage

# Run quality checks
make lint                                   # Code linting
make format                                 # Code formatting
uv run mypy --strict src/ scripts/         # Type checking
```

### Test Architecture

- **Unit Tests**: Mock external dependencies, test individual components
- **Integration Tests**: Validate component interactions and workflows
- **Makefile Tests**: Ensure build automation reliability
- **CI/CD Integration**: GitHub Actions with automated testing

> 📋 **For detailed testing documentation, see [docs/TESTING_DOCUMENTATION.md](docs/TESTING_DOCUMENTATION.md)**

## 🤝 Development

> 📚 **For comprehensive development workflow documentation, see [docs/development_workflow.md](docs/development_workflow.md)**

### Development Workflow

1. **Fork and clone** the repository
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Set up development environment**: `make dev-install`
4. **Make your changes** with proper testing
5. **Run quality checks**: `make lint test`
6. **Commit changes**: `git commit -m 'Add amazing feature'`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Code Quality Standards

- ✅ **Type hints** required for all functions
- ✅ **Docstrings** for all public methods
- ✅ **Unit tests** for new functionality
- ✅ **Ruff formatting** and linting compliance
- ✅ **Pre-commit hooks** must pass

### Development Tools

This project leverages modern Python development tools:

- **[UV](https://github.com/astral-sh/uv)** - Ultra-fast Python package manager
- **[Ruff](https://github.com/astral-sh/ruff)** - Lightning-fast linting and formatting
- **[MyPy](https://mypy.readthedocs.io/)** - Static type checking
- **[Pytest](https://pytest.org/)** - Advanced testing framework
- **[Pre-commit](https://pre-commit.com/)** - Git hook management
- **[Rich](https://rich.readthedocs.io/)** - Beautiful terminal interfaces

## 📖 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- 📋 **[Architecture Specification](docs/planning/homelab_spec.md)** - Detailed system design
- 🔄 **[Supabase Migration Guide](docs/SUPABASE_MIGRATION.md)** - Database migration procedures
- 📝 **[UV Implementation Guide](docs/uv_implementation_summary.md)** - Package management best practices
- 🔧 **[Supabase Refactoring](docs/supabase_refactoring_summary.md)** - Infrastructure improvements

## 🛣️ Roadmap

### Phase 1: Foundation (Current)

- ✅ UV package manager integration
- ✅ Supabase infrastructure automation
- ✅ System auditing and health checks
- 🔄 CLI interface development

### Phase 2: Enhancement (Planned)

- 📋 Ansible playbook development
- 🐳 Container orchestration improvements
- 📊 Advanced monitoring dashboards
- 🔐 Enhanced security protocols

### Phase 3: Intelligence (Future)

- 🤖 AI-powered system optimization
- 📈 Predictive maintenance
- 🔄 Automated scaling policies
- 📱 Mobile management interfaces

## 🆘 Troubleshooting

<details>
<summary>Common Issues and Solutions</summary>

### UV Installation Issues

```bash
# If UV installation fails, install manually:
pip install uv
# Then run: make all
```

### WSL2 Network Configuration

```bash
# Check WSL2 networking:
homelab audit
# Follow the network configuration recommendations
```

### Kubernetes Connectivity

```bash
# Verify K3s cluster status:
kubectl cluster-info
# Check pod status:
kubectl get pods -A
```

### Permission Issues

```bash
# Fix SSH key permissions:
chmod 600 ~/.ssh/id_rsa
# Fix script permissions:
chmod +x scripts/*.py
```

</details>

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Astral](https://astral.sh/)** for the incredible UV package manager
- **[Supabase](https://supabase.com/)** for the open-source Firebase alternative
- **[K3s](https://k3s.io/)** for lightweight Kubernetes
- **[Rich](https://rich.readthedocs.io/)** for beautiful terminal interfaces

## 📞 Support

- 📖 **Documentation**: Check the [docs/](docs/) directory
- 🐛 **Bug Reports**: Open an issue with detailed reproduction steps
- 💡 **Feature Requests**: Describe your use case and proposed solution
- 💬 **Questions**: Start a discussion for general questions

---

<div align="center">
<strong>Built with ❤️ for the homelab community</strong>
<br/>
<sub>Making infrastructure automation accessible and enjoyable</sub>
</div>
