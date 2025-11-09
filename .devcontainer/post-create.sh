#!/bin/bash

echo "🚀 Setting up AutoStrategist-AI Development Environment..."

# Install Poetry
echo "📦 Installing Poetry..."
curl -sSL https://install.python-poetry.org | python3 -
export PATH="/home/vscode/.local/bin:$PATH"

# Configure Poetry to create virtual environments in project
poetry config virtualenvs.in-project true

# Install project dependencies
echo "📦 Installing Python dependencies with Poetry..."
if [ -f "pyproject.toml" ]; then
    poetry install
else
    echo "⚠️  pyproject.toml not found."
    exit 1
fi

# Configure Databricks CLI (if not already configured)
echo "🔧 Checking Databricks configuration..."
if [ ! -f ~/.databrickscfg ]; then
    echo "⚠️  Databricks config not found. You'll need to run 'databricks configure' manually."
fi

# Initialize Databricks Asset Bundles if databricks.yml doesn't exist
if [ ! -f "databricks.yml" ]; then
    echo "📝 Databricks Asset Bundle config not found. You can initialize it with 'databricks bundle init'."
fi

# Create project structure if it doesn't exist
echo "📁 Setting up project structure..."
mkdir -p src/ingestion
mkdir -p src/transformation
mkdir -p src/agent
mkdir -p src/utils
mkdir -p apps
mkdir -p tests

# Configure Git
echo "🔧 Configuring Git..."
if [ ! -f ~/.gitconfig ]; then
    echo "⚠️  Git config not found. Setting up basic configuration..."
    git config --global init.defaultBranch main
    git config --global core.autocrlf input
fi

# Set up git hooks (optional)
if [ -d ".git" ]; then
    echo "🎣 Setting up git hooks..."
    # Add pre-commit hook for formatting
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
poetry run black --check src/ apps/ tests/
if [ $? -ne 0 ]; then
    echo "❌ Code formatting check failed. Run 'poetry run black src/ apps/ tests/' to fix."
    exit 1
fi
EOF
    chmod +x .git/hooks/pre-commit
fi

echo "✅ Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Configure Git: git config --global user.name 'Your Name' && git config --global user.email 'your.email@example.com'"
echo "   2. Configure Databricks: databricks configure --token"
echo "   3. Initialize DABs: databricks bundle init"
echo "   4. Start developing!"
echo ""
echo "🔗 Useful commands:"
echo "   - poetry add <package>: Add a new dependency"
echo "   - poetry run <command>: Run commands in Poetry environment"
echo "   - poetry shell: Activate Poetry virtual environment"
echo "   - databricks bundle validate: Validate your DABs configuration"
echo "   - databricks bundle deploy: Deploy to Databricks"
echo "   - poetry run streamlit run apps/app.py: Run the frontend locally"
echo ""
