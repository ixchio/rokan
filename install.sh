#!/bin/bash
# Rokan Skill Pack Installer for OpenClaw
# The Player. Linux-first. No cloud leaks.

set -e

ROKAN_VERSION="1.0.0"
ROKAN_DIR="$HOME/.rokan"
OPENCLAW_SKILLS="$HOME/.openclaw/skills"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
    ██████╗  ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔═══██╗██║ ██╔╝██╔══██╗████╗  ██║
    ██████╔╝██║   ██║█████╔╝ ███████║██╔██╗ ██║
    ██╔══██╗██║   ██║██╔═██╗ ██╔══██║██║╚██╗██║
    ██║  ██║╚██████╔╝██║  ██╗██║  ██║██║ ╚████║
    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
    
    The Player. Linux-first. No cloud leaks.
    Sung Jin-Woo Edition for OpenClaw
EOF
    echo -e "${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Node.js version
    if ! command -v node &> /dev/null; then
        log_error "Node.js not found. Please install Node.js 22+ first."
        exit 1
    fi
    
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 22 ]; then
        log_error "Node.js 22+ required. Found: $(node -v)"
        exit 1
    fi
    log_success "Node.js $(node -v)"
    
    # Check OpenClaw
    if ! command -v openclaw &> /dev/null; then
        log_warn "OpenClaw not found. Installing..."
        npm install -g openclaw@latest
    fi
    log_success "OpenClaw installed"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found. Please install Python 3.10+"
        exit 1
    fi
    log_success "Python $(python3 --version)"
    
    # Check Docker (optional)
    if command -v docker &> /dev/null; then
        log_success "Docker found"
        HAS_DOCKER=true
    else
        log_warn "Docker not found. Some features will be limited."
        HAS_DOCKER=false
    fi
}

install_openclaw() {
    log_info "Installing OpenClaw..."
    npm install -g openclaw@latest
    openclaw onboard --install-daemon
    log_success "OpenClaw installed and daemon configured"
}

create_directories() {
    log_info "Creating Rokan directories..."
    
    mkdir -p "$ROKAN_DIR"/{logs,models,sandbox,vcr_recordings,scripts}
    mkdir -p "$OPENCLAW_SKILLS"
    mkdir -p "$ROKAN_DIR/qdrant/storage"
    
    log_success "Directories created"
}

install_skills() {
    log_info "Installing Rokan skills to OpenClaw..."
    
    # Copy skills to OpenClaw directory
    SKILL_SRC="$(dirname "$0")"
    
    for skill in rokan-memory rokan-voice rokan-research rokan-jobs rokan-system rokan-code rokan-vcr; do
        if [ -d "$SKILL_SRC/$skill" ]; then
            cp -r "$SKILL_SRC/$skill" "$OPENCLAW_SKILLS/"
            log_success "Installed $skill"
        else
            log_warn "Skill $skill not found in source"
        fi
    done
}

install_config() {
    log_info "Installing Rokan configuration..."
    
    SKILL_SRC="$(dirname "$0")"
    
    # Backup existing config
    if [ -f "$HOME/.openclaw/config.yaml" ]; then
        cp "$HOME/.openclaw/config.yaml" "$HOME/.openclaw/config.yaml.backup.$(date +%s)"
        log_warn "Backed up existing OpenClaw config"
    fi
    
    # Copy new config
    if [ -f "$SKILL_SRC/config.yaml" ]; then
        cp "$SKILL_SRC/config.yaml" "$HOME/.openclaw/config.yaml"
        log_success "Rokan configuration installed"
    else
        log_warn "Config file not found in source"
    fi
}

install_python_deps() {
    log_info "Installing Python dependencies..."
    
    pip3 install --user -q \
        qdrant-client \
        ollama \
        mem0ai \
        crawl4ai \
        praw \
        tweepy \
        tavily-python \
        psutil \
        pydbus \
        restrictedpython \
        openwakeword \
        pyaudio \
        webrtcvad \
        numpy \
        scipy \
        rich \
        textual \
        pyyaml \
        pydantic \
        python-dotenv \
        apscheduler \
        discord-webhook \
        ai-agent-vcr 2>/dev/null || log_warn "Some packages may need manual installation"
    
    log_success "Python dependencies installed"
}

setup_ollama() {
    log_info "Setting up Ollama..."
    
    if ! command -v ollama &> /dev/null; then
        log_warn "Ollama not found. Installing..."
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    
    # Pull required models
    log_info "Pulling required models (this may take a while)..."
    ollama pull deepseek-r2:7b || log_warn "deepseek-r2:7b pull failed"
    ollama pull mxbai-embed-large || log_warn "mxbai-embed-large pull failed"
    ollama pull nemotron-nano:4b || log_warn "nemotron-nano:4b pull failed"
    
    log_success "Ollama models ready"
}

setup_qdrant() {
    log_info "Setting up Qdrant..."
    
    if [ "$HAS_DOCKER" = true ]; then
        docker run -d \
            --name rokan-qdrant \
            -p 6333:6333 \
            -v "$ROKAN_DIR/qdrant/storage:/qdrant/storage" \
            --restart unless-stopped \
            qdrant/qdrant 2>/dev/null || log_warn "Qdrant container may already exist"
        
        log_success "Qdrant running on localhost:6333"
    else
        log_warn "Docker not available. Please install Qdrant manually."
    fi
}

setup_voice() {
    log_info "Setting up voice pipeline..."
    
    MODELS_DIR="$ROKAN_DIR/models"
    
    # Download Whisper model
    if [ ! -f "$MODELS_DIR/whisper-base.bin" ]; then
        log_info "Downloading Whisper model..."
        wget -q -O "$MODELS_DIR/whisper-base.bin" \
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin" || \
            log_warn "Whisper model download failed"
    fi
    
    # Download Piper voice
    PIPER_DIR="$MODELS_DIR/piper"
    mkdir -p "$PIPER_DIR"
    
    if [ ! -f "$PIPER_DIR/voice.onnx" ]; then
        log_info "Downloading Piper voice model..."
        wget -q -O "$PIPER_DIR/voice.onnx" \
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" || \
            log_warn "Piper voice download failed"
        
        wget -q -O "$PIPER_DIR/voice.onnx.json" \
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" || \
            log_warn "Piper config download failed"
    fi
    
    log_success "Voice models ready"
}

create_env_file() {
    log_info "Creating environment template..."
    
    cat > "$ROKAN_DIR/.env.template" << 'EOF'
# Rokan Environment Variables
# Copy to .env and fill in your keys

# LLM Fallback APIs (optional - local Ollama works without these)
GROQ_API_KEY=your_groq_key_here
NVIDIA_API_KEY=your_nvidia_key_here

# Research APIs (optional)
TAVILY_API_KEY=your_tavily_key_here
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
TWITTER_BEARER_TOKEN=your_twitter_token

# Notifications (optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook
EOF

    log_success "Environment template created at $ROKAN_DIR/.env.template"
}

print_next_steps() {
    echo -e "\n${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ROKAN INSTALLATION COMPLETE                   ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}\n"
    
    echo -e "${BLUE}Next Steps:${NC}"
    echo ""
    echo "1. ${YELLOW}Set up API keys (optional):${NC}"
    echo "   cp ~/.rokan/.env.template ~/.rokan/.env"
    echo "   nano ~/.rokan/.env"
    echo ""
    echo "2. ${YELLOW}Start OpenClaw with Rokan:${NC}"
    echo "   openclaw start"
    echo ""
    echo "3. ${YELLOW}Test Rokan:${NC}"
    echo "   openclaw chat 'Hey Rokan, system status'"
    echo ""
    echo "4. ${YELLOW}Enable voice mode (optional):${NC}"
    echo "   openclaw config voice.enabled=true"
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo "   Skills: ~/.openclaw/skills/rokan/"
    echo "   Config: ~/.openclaw/config.yaml"
    echo "   Logs:   ~/.rokan/logs/"
    echo ""
    echo -e "${GREEN}Rokan is ready. Execute.${NC}"
}

main() {
    print_banner
    
    log_info "Rokan Skill Pack v$ROKAN_VERSION for OpenClaw"
    log_info "Installing..."
    
    check_prerequisites
    create_directories
    install_skills
    install_config
    install_python_deps
    setup_ollama
    setup_qdrant
    setup_voice
    create_env_file
    
    print_next_steps
}

# Run main function
main "$@"
