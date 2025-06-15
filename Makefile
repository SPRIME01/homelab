# Smart Home K3s Lab Makefile
# UV-based Python project management

.PHONY: all install verify audit clean help
.PHONY: health-check discover backup optimize update-all dev-setup
.PHONY: dev-install dev-reset quick-test monitor status disaster-recovery

# Check if UV is available
UV_AVAILABLE := $(shell command -v uv 2> /dev/null)

# Ensure UV is installed
check-uv:
ifndef UV_AVAILABLE
	@echo "❌ UV package manager not found. Installing..."
	pip install uv
	@echo "✅ UV installed successfully"
endif

# Main installation targets
all: check-uv audit install verify ## Run complete installation process

audit: check-uv ## Run system audit
	@echo "🔍 Running system audit..."
	uv run python scripts/00-system-audit.py

install: check-uv ## Install all components
	@echo "⚙️ Installing homelab components..."
	uv run python scripts/01-install-components.py

verify: check-uv ## Verify installation
	@echo "✅ Verifying installation..."
	@command -v kubectl >/dev/null 2>&1 && echo "✅ kubectl installed" || echo "❌ kubectl missing"
	@command -v k3s >/dev/null 2>&1 && echo "✅ k3s installed" || echo "❌ k3s missing"
	@systemctl is-active --quiet k3s && echo "✅ k3s service running" || echo "❌ k3s service not running"

clean: ## Clean up installation artifacts
	@echo "🧹 Cleaning up..."
	@rm -rf logs/ .pytest_cache/ __pycache__/ *.egg-info/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Development environment
dev-install: check-uv ## Install development dependencies
	@echo "🔧 Installing development environment..."
	uv sync --all-extras

dev-reset: clean dev-install ## Reset development environment
	@echo "🔄 Resetting development environment..."
	uv run pre-commit install
	@echo "✅ Development environment reset complete"

# Additional utility targets
health-check: check-uv ## Run comprehensive cluster health check
	@echo "🏥 Running cluster health check..."
	uv run python scripts/cluster-heath-monitor.py --check-all

discover: check-uv ## Discover smart home devices on network
	@echo "🔍 Discovering smart home devices..."
	uv run python scripts/homelab-discovery.py --scan --generate-configs

backup: check-uv ## Create full system backup
	@echo "💾 Creating full system backup..."
	uv run python scripts/backup-manager.py --full-backup

optimize: check-uv ## Analyze and optimize system performance
	@echo "⚡ Analyzing system performance..."
	uv run python scripts/performance-optimizer.py --analyze --apply-optimizations

update-all: check-uv ## Safely update all components
	@echo "🔄 Checking and applying updates..."
	uv run python scripts/update-manager.py --check-all --safe-update

dev-setup: check-uv ## Setup optimal development environment
	@echo "💻 Setting up development environment..."
	uv run python scripts/dev-env-manager.py --setup-all

# Monitoring and maintenance
monitor: check-uv ## Start continuous monitoring
	@echo "📊 Starting continuous monitoring..."
	uv run python scripts/cluster-heath-monitor.py --continuous --interval 300 &

# Quick status checks
status: check-uv ## Show comprehensive system status
	@echo "📈 Homelab Status Dashboard"
	@echo "=========================="
	@make health-check
	@echo ""
	@make verify
	@echo ""
	@echo "🏠 Home Assistant Status:"
	-curl -s http://192.168.0.41:8123/api/ | jq .message || echo "Home Assistant not accessible"

# Development workflow helpers
quick-test: check-uv ## Quick smoke tests
	@echo "🧪 Running quick smoke tests..."
	uv run pytest tests/smoke/ -v

# Advanced operations
disaster-recovery: ## Show disaster recovery options
	@echo "🚨 Disaster Recovery Options:"
	@echo "1. Restore from backup: uv run python scripts/backup-manager.py --restore <path>"
	@echo "2. Rebuild cluster: make clean && make all"
	@echo "3. Emergency contacts and procedures in docs/disaster-recovery.md"

help: ## Show this help message
	@echo "Smart Home K3s Lab - Available Commands:"
	@echo "========================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
