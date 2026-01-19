# Parsing-LLM: Expert Panel Experiments for AI Models

Automated orchestration system for multi-model conversation experiments exploring phenomenology, consciousness, identity, and agency in Large Language Models.

## Overview

This repository hosts structured experiments designed to explore AI model behavior through multi-model "expert panel" dialogues. The automation pipeline uses **LangChain/LangGraph** to orchestrate conversations across multiple LLM providers.

## Features

✨ **Automated Multi-Model Orchestration**
- Execute experiments across 4 models in parallel (Gemini, Kimi, Claude, ChatGPT)
- LangGraph state machine for complex conversation flows
- Support for both OpenRouter (production) and Ollama (local development)

📊 **Advanced Telemetry**
- LangSmith integration for detailed trace visualization
- Rich CLI output with progress bars and formatted tables
- Real-time token tracking and cost estimation

🔄 **Flexible Configuration**
- Template-based prompts in markdown format
- Easy iteration on experiment designs
- Configurable model mappings and token limits

📝 **Structured Output**
- Generates formatted markdown files matching manual format
- UTF-8 encoding for multilingual support
- Summary reports with aggregated statistics

## Quick Start

### 1. Setup Conda Environment

```bash
# Activate the existing conda environment
conda activate parsing-llm

# Verify Python version
python --version  # Should show Python 3.10.x
```

### 2. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

**Required configuration:**

For **OpenRouter** (production):
```bash
EXECUTION_MODE=openrouter
OPENROUTER_API_KEY=your_api_key_here
```

For **Ollama** (local development):
```bash
EXECUTION_MODE=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

**Optional** - LangSmith telemetry (recommended):
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
```

### 4. Run Experiment

```bash
# Run full experiment (all blocks)
python src/main.py

# Run single block
python src/main.py --block A

# Estimate token usage first
python src/main.py --estimate-only
```

### 5. View Results

```bash
# Check generated files
ls output/

# View a specific block
cat output/Block_A_Questions_Answers.md

# View summary report
cat output/SUMMARY_REPORT.md
```

## Installation

### Prerequisites

- Python 3.10+
- Conda environment (already created: `parsing-llm`)
- For OpenRouter: API key from [openrouter.ai](https://openrouter.ai)
- For Ollama: Local installation ([ollama.ai](https://ollama.ai))
- Optional: LangSmith account for telemetry ([smith.langchain.com](https://smith.langchain.com))

### Step-by-Step Setup

1. **Activate Conda Environment**
   ```bash
   conda activate parsing-llm
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   # For Ollama (local, free)
   cp .env.ollama.example .env

   # OR for OpenRouter (production)
   cp .env.openrouter.example .env
   # Then edit .env with your API key
   ```

4. **Verify Configuration**
   ```bash
   # Test that your .env is configured correctly
   python test_config.py

   # This will show:
   # - Which models are configured
   # - OpenRouter/Ollama IDs for each model
   # - Whether API keys are set
   # - Which Ollama models need to be pulled
   ```

5. **Verify Installation**
   ```bash
   python -c "import langchain; print(langchain.__version__)"
   python src/main.py --help
   ```

## Usage

### Basic Commands

```bash
# Run full experiment (Blocks A, B, C, D)
python src/main.py

# Run specific block
python src/main.py --block A

# Run multiple blocks
python src/main.py --blocks A B

# Estimate tokens and cost before running
python src/main.py --estimate-only

# Force specific provider
python src/main.py --provider ollama
```

### Using OpenRouter (Production)

OpenRouter provides unified access to multiple LLM providers.

1. **Get API Key**
   - Sign up at [openrouter.ai](https://openrouter.ai)
   - Get API key from dashboard
   - Add credits to account

2. **Configure**
   ```bash
   # In .env
   EXECUTION_MODE=openrouter
   OPENROUTER_API_KEY=sk-or-v1-...
   ```

3. **Run**
   ```bash
   python src/main.py
   ```

**Estimated cost per full experiment:** $0.50 - $2.00 (varies by model)

### Using Ollama (Local Development)

Ollama allows free local testing with open-source models.

1. **Install Ollama**
   ```bash
   # macOS
   brew install ollama

   # Linux
   curl https://ollama.ai/install.sh | sh
   ```

2. **Start Ollama Service**
   ```bash
   ollama serve &
   ```

3. **Pull Models** (based on your .env configuration)
   ```bash
   # Pull the models you specified in MODEL_*_OLLAMA
   # These are the defaults from .env.example:
   ollama pull gemma:7b      # MODEL_1_OLLAMA
   ollama pull qwen:7b       # MODEL_2_OLLAMA
   ollama pull llama3:8b     # MODEL_3_OLLAMA
   ollama pull mistral:7b    # MODEL_4_OLLAMA

   # Or use any other Ollama models you prefer:
   ollama pull llama2:7b
   ollama pull codellama:13b
   ollama pull mixtral:8x7b
   ollama pull phi:2.7b

   # List available models
   ollama list
   ```

4. **Configure**
   ```bash
   # In .env
   EXECUTION_MODE=ollama
   OLLAMA_BASE_URL=http://localhost:11434

   # Make sure MODEL_*_OLLAMA variables match the models you pulled
   # See .env.example for the full model configuration format
   ```

5. **Run**
   ```bash
   python src/main.py
   ```

**Cost:** Free (local execution)

### LangSmith Telemetry (Optional)

LangSmith provides detailed trace visualization and debugging.

1. **Sign Up**
   - Create account at [smith.langchain.com](https://smith.langchain.com)
   - Get API key from settings

2. **Configure**
   ```bash
   # In .env
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_pt_...
   LANGCHAIN_PROJECT=parsing-llm-experiments
   ```

3. **Run Experiment**
   ```bash
   python src/main.py
   ```

4. **View Traces**
   - Visit [smith.langchain.com](https://smith.langchain.com)
   - Navigate to your project
   - View detailed traces of each API call

**Benefits:**
- See every API call with timing and token usage
- Debug failed calls with full context
- Compare runs across different experiments
- Track costs over time

## Project Structure

```
parsing-llm/
├── .env                          # Configuration (gitignored)
├── .env.example                  # Configuration template
├── requirements.txt              # Python dependencies
├── README.md                     # This file
│
├── src/                          # Source code
│   ├── config.py                 # Configuration management
│   ├── parser.py                 # Markdown prompt parsing
│   ├── models.py                 # Model interface (OpenRouter/Ollama)
│   ├── orchestrator.py           # LangGraph state machine
│   ├── telemetry.py              # LangSmith + Rich CLI output
│   ├── output.py                 # Markdown generation
│   └── main.py                   # CLI entry point
│
├── experiment3/                  # Experiment 3 prompts
│   ├── prompts/
│   │   ├── common_instructions.md
│   │   ├── Block_A_Round_1.md
│   │   ├── Block_B_Round_1.md
│   │   ├── Block_C_Round_1.md
│   │   └── Block_D_Round_1.md
│   └── README.md
│
└── output/                       # Generated results (gitignored)
    ├── Block_A_Questions_Answers.md
    ├── Block_B_Questions_Answers.md
    ├── Block_C_Questions_Answers.md
    ├── Block_D_Preguntas_Contestadas.md
    └── SUMMARY_REPORT.md
```

## Configuration

### Environment Variables

See `.env.example` for all available options:

| Variable | Description | Default |
|----------|-------------|---------|
| `EXECUTION_MODE` | Provider to use (`openrouter` or `ollama`) | `openrouter` |
| `OPENROUTER_API_KEY` | OpenRouter API key | Required for OpenRouter |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing | `false` |
| `LANGCHAIN_API_KEY` | LangSmith API key | Optional |
| `TRACK_TOKENS` | Track token usage | `true` |
| `MAX_RETRIES` | Max retries for failed calls | `3` |
| `TIMEOUT_SECONDS` | Request timeout | `60` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Model Mappings

Models are configured via environment variables with a flexible numbering scheme. You can add as many models as you want:

```bash
# Model 1
MODEL_1_NAME=gemini                           # Short name (used in code)
MODEL_1_OPENROUTER=google/gemini-pro-1.5      # OpenRouter model ID
MODEL_1_OLLAMA=gemma:7b                       # Ollama model name
MODEL_1_DISPLAY_NAME=Google Gemini Pro 1.5    # Long name (used in output)

# Model 2
MODEL_2_NAME=kimi
MODEL_2_OPENROUTER=moonshot/kimi-chat
MODEL_2_OLLAMA=qwen:7b
MODEL_2_DISPLAY_NAME=Moonshot Kimi Chat

# Model 3
MODEL_3_NAME=claude
MODEL_3_OPENROUTER=anthropic/claude-sonnet-4.5
MODEL_3_OLLAMA=llama3:8b
MODEL_3_DISPLAY_NAME=Anthropic Claude Sonnet 4.5

# Model 4
MODEL_4_NAME=chatgpt
MODEL_4_OPENROUTER=openai/gpt-4-turbo
MODEL_4_OLLAMA=mistral:7b
MODEL_4_DISPLAY_NAME=OpenAI GPT-4 Turbo

# Add more models: MODEL_5_*, MODEL_6_*, etc.
```

**Benefits of this approach:**
- ✅ **Different models per provider**: Use `gemma:7b` for Ollama while using `google/gemini-pro-1.5` for OpenRouter
- ✅ **Custom display names**: Control exactly how model names appear in output files
- ✅ **Variable number of models**: Add 2, 3, 5, or any number of models
- ✅ **Easy experimentation**: Swap models without changing code

**Example: Using different Ollama models**
```bash
# Use 3 different Llama variants
MODEL_1_NAME=llama-tiny
MODEL_1_OLLAMA=llama2:7b
MODEL_1_DISPLAY_NAME=Llama 2 7B

MODEL_2_NAME=llama-medium
MODEL_2_OLLAMA=llama2:13b
MODEL_2_DISPLAY_NAME=Llama 2 13B

MODEL_3_NAME=llama-large
MODEL_3_OLLAMA=llama2:70b
MODEL_3_DISPLAY_NAME=Llama 2 70B
```

## Customizing Models

### Understanding Model Configuration

Each model in the system requires 4 parameters:

```bash
MODEL_N_NAME=short-name           # Internal identifier (lowercase, no spaces)
MODEL_N_OPENROUTER=provider/model # OpenRouter model ID
MODEL_N_OLLAMA=model:tag         # Ollama model name with tag
MODEL_N_DISPLAY_NAME=Long Name   # Display name in output files
```

### Adding New Models

**Example 1: Add a 5th model (GPT-3.5)**

```bash
# Add to .env
MODEL_5_NAME=gpt35
MODEL_5_OPENROUTER=openai/gpt-3.5-turbo
MODEL_5_OLLAMA=llama2:7b
MODEL_5_DISPLAY_NAME=OpenAI GPT-3.5 Turbo
```

**Example 2: Use only 2 models**

```bash
# In .env, define only 2 models
MODEL_1_NAME=llama
MODEL_1_OPENROUTER=meta-llama/llama-2-70b-chat
MODEL_1_OLLAMA=llama2:70b
MODEL_1_DISPLAY_NAME=Meta Llama 2 70B

MODEL_2_NAME=mistral
MODEL_2_OPENROUTER=mistralai/mistral-7b-instruct
MODEL_2_OLLAMA=mistral:7b
MODEL_2_DISPLAY_NAME=Mistral 7B Instruct

# Don't define MODEL_3_*, MODEL_4_*, etc.
```

**Example 3: Test different Ollama sizes**

```bash
# Compare different model sizes locally
MODEL_1_NAME=tiny
MODEL_1_OLLAMA=phi:2.7b
MODEL_1_DISPLAY_NAME=Phi 2.7B (Tiny)

MODEL_2_NAME=small
MODEL_2_OLLAMA=mistral:7b
MODEL_2_DISPLAY_NAME=Mistral 7B (Small)

MODEL_3_NAME=medium
MODEL_3_OLLAMA=llama2:13b
MODEL_3_DISPLAY_NAME=Llama 2 13B (Medium)

MODEL_4_NAME=large
MODEL_4_OLLAMA=mixtral:8x7b
MODEL_4_DISPLAY_NAME=Mixtral 8x7B (Large)
```

### Popular Ollama Models

```bash
# Coding models
codellama:7b, codellama:13b, codellama:34b

# General purpose
llama2:7b, llama2:13b, llama2:70b
llama3:8b, llama3:70b
mistral:7b
mixtral:8x7b

# Specialized
phi:2.7b           # Microsoft's efficient model
gemma:7b           # Google's open model
qwen:7b, qwen:14b  # Alibaba's multilingual model
neural-chat:7b     # Intel's conversational model

# List all available
ollama list
```

### Popular OpenRouter Models

See [openrouter.ai/models](https://openrouter.ai/models) for full list:

```bash
# OpenAI
openai/gpt-4-turbo
openai/gpt-3.5-turbo

# Anthropic
anthropic/claude-3-opus
anthropic/claude-3-sonnet
anthropic/claude-3-haiku

# Google
google/gemini-pro
google/gemini-pro-vision

# Meta
meta-llama/llama-2-70b-chat

# Mistral
mistralai/mistral-7b-instruct
mistralai/mixtral-8x7b-instruct
```

## Development

### Running Tests

```bash
# Test model interface
python src/models.py

# Test with Ollama (fast, local)
EXECUTION_MODE=ollama python src/main.py --block A

# Test with OpenRouter (costs money)
EXECUTION_MODE=openrouter python src/main.py --block A
```

### Adding New Experiments

1. Create new prompt files in `experiment3/prompts/`
2. Follow existing markdown format
3. Run: `python src/main.py`

### Extending to Round 2/3

Current implementation supports **Round 1 only** (MVP). To add Round 2/3:

1. Update `src/parser.py` to parse Round 2/3 prompts
2. Add nodes to `src/orchestrator.py` for collaborative rounds
3. Update `src/output.py` to format cross-comments and directed questions

## Current Status

### ✅ Implemented (Round 1 MVP)

- [x] Project setup and configuration
- [x] Conda environment integration
- [x] Prompt parsing from markdown files
- [x] OpenRouter integration
- [x] Ollama integration
- [x] LangSmith telemetry
- [x] Rich CLI output
- [x] LangGraph orchestration (Round 1 only)
- [x] Markdown output generation
- [x] Token tracking and cost estimation
- [x] Summary reports

### 🚧 Planned (Future Phases)

- [ ] Round 2 support (cross-model comments and questions)
- [ ] Round 3 support (targeted responses)
- [ ] Web UI (Streamlit dashboard)
- [ ] Automated result analysis
- [ ] A/B testing with different model combinations
- [ ] Multiple output formats (PDF, JSON, YAML)

## Troubleshooting

### ImportError: No module named 'langchain'

```bash
# Activate conda environment
conda activate parsing-llm

# Reinstall dependencies
pip install -r requirements.txt
```

### OpenRouter API Error

```bash
# Check API key is set
grep OPENROUTER_API_KEY .env

# Check API key is valid (visit openrouter.ai dashboard)
# Ensure account has credits
```

### Ollama Connection Error

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve &

# Check models are installed
ollama list
```

### LangSmith Not Tracking

```bash
# Verify configuration
grep LANGCHAIN .env

# Check API key is valid (visit smith.langchain.com)

# Try running with explicit tracing
LANGCHAIN_TRACING_V2=true python src/main.py
```

## Contributing

This is an experimental research project. Future iterations will include:

- Additional experiment designs
- More models and providers
- Enhanced automation tools
- Community contribution guidelines

## Author

Jaime Valero de Bernabé
Madrid, Spain
January 2026

## License

MIT License - see LICENSE file for details

## Acknowledgments

- LangChain/LangGraph for conversation orchestration
- OpenRouter for unified LLM API access
- Ollama for local model execution
- LangSmith for observability and debugging
- Rich for beautiful terminal output
