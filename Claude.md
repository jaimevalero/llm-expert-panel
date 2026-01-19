# Parsing-LLM: Expert Panel Experiments for AI Models

## Project Overview

This repository hosts a series of structured experiments designed to explore phenomenology, consciousness, identity, and agency in Large Language Models through multi-model "expert panel" dialogues.

## Repository Objectives

### 1. Standardization and Sharing

- **Homogenize experiment structure** for consistency across future experiments
- **Facilitate result sharing** with the research community
- **Document methodology** for reproducibility
- **Provide templates** for similar explorations

### 2. Automation Pipeline

**Goal:** Create a script to automate the generation of experiment files and orchestrate multi-model conversations.

**Planned Implementation:**

- **Framework:** LangChain / LangGraph for conversation orchestration
- **API Interface:** OpenRouter for unified access to multiple LLM providers
- **Token Management:** Pre-calculate token budgets per experiment to ensure feasibility
- **Session Handling:** Investigate conversation persistence options across providers

**Key Features to Develop:**

```python
# Pseudocode for automation pipeline
- Extract questions and model configurations from prompt templates
- Dynamically generate prompts per model and round
- Orchestrate multi-round conversations
- Aggregate and format responses
- Calculate token usage and costs
- Allow compatibility with locals models using ollama (just for develop)
```

### 3. Template Flexibility

**Extract and Parameterize:**

- Questions/prompts from experiment structure
- Model names and configurations
- Round structures and token limits
- Evaluation criteria

**Benefits:**

- Easy iteration on experiment designs
- Rapid testing of new question sets
- Simple addition of new models
- Reusable framework for different research questions

## Current Status

### Completed ✓ (Phase 1: MVP - Round 1 Only)

- [X] Experiment 3 structure defined
- [X] Manual execution with 4 models (Gemini, Kimi, Claude, ChatGPT)
- [X] Results documented in Blocks A, B, C, and D
- [X] Executive summary generated
- [X] **Automation Pipeline Implemented** (January 2026)
  - [X] Project structure and configuration management
  - [X] Conda environment integration (Python 3.10)
  - [X] LangChain/LangGraph orchestration
  - [X] OpenRouter API integration
  - [X] Ollama local model support
  - [X] LangSmith telemetry and tracing
  - [X] Rich CLI output with progress bars
  - [X] Markdown prompt parser
  - [X] Markdown output generator
  - [X] Token tracking and cost estimation
  - [X] Error handling and retries
  - [X] Summary report generation
  - [X] Complete documentation (README.md)

### In Progress 🔄

- [ ] Testing with OpenRouter (production)
- [ ] Testing with Ollama (local development)
- [ ] Validation of output format vs manual results

### Planned 📋 (Phase 2: Full Implementation)

- [ ] Round 2 support (cross-model comments and questions)
- [ ] Round 3 support (targeted responses)
- [ ] Multi-round conversation state persistence
- [ ] Web UI (Streamlit dashboard)
- [ ] Automated result analysis and comparison
- [ ] A/B testing with different model combinations
- [ ] Multiple output formats (PDF, JSON, YAML)

## Technical Considerations

### Token Budget Calculator

```python
# Estimated tokens per experiment
Experiment 3:
- Block A: (1600 + 1000 + 400) × 4 models = 12,000 tokens
- Block B: (1400 + 1000 + 400) × 4 models = 11,200 tokens
- Block C: 1500 × 4 models = 6,000 tokens
- Total output: ~29,200 tokens
- Input tokens (prompts + context): ~15,000-20,000 tokens
- Grand total: ~44,200-49,200 tokens per full experiment run
```

### OpenRouter Integration

**Advantages:**

- Unified API for multiple providers
- Consistent pricing and rate limits
- Simplified model switching

**Questions to Resolve:**

- Does OpenRouter persist conversation context across rounds?
- Rate limits for batch processing multiple models
- Cost optimization strategies

## Repository Structure

```
parsing-llm/
├── experiment3/          # Current experiment on phenomenology
│   ├── prompts/         # Structured prompts by block and round
│   ├── README.md        # Experiment documentation
│   ├── EXECUTIVE_SUMMARY.md
│   └── all-raw-conversations.md
├── Block_A_Questions_Answers.md
├── Block_B_Questions_Answers.md
├── Block_C_Questions_Answers.md
├── Block_D_Preguntas_Contestadas.md
└── Claude.md (this file) # Project roadmap and TODO
```

## Using the Automation Pipeline

### Quick Start

```bash
# 1. Activate conda environment
conda activate parsing-llm

# 2. Install dependencies (if not already done)
pip install -r requirements.txt

# 3. Configure .env
cp .env.example .env
# Edit .env with your API keys

# 4. Run experiment
python src/main.py

# 5. View results
ls output/
```

### Common Commands

```bash
# Estimate token usage before running
python src/main.py --estimate-only

# Run single block
python src/main.py --block A

# Run with Ollama (local, free)
python src/main.py --provider ollama

# Run with OpenRouter (production)
python src/main.py --provider openrouter
```

### Output Files

Generated files in `output/` directory:

- `Block_A_Questions_Answers.md` - Block A responses
- `Block_B_Questions_Answers.md` - Block B responses
- `Block_C_Questions_Answers.md` - Block C responses
- `Block_D_Preguntas_Contestadas.md` - Block D responses (Spanish)
- `SUMMARY_REPORT.md` - Aggregated statistics

## Next Steps

### Phase 2: Round 2/3 Support

1. **Round 2 Implementation**
   - Extend parser to extract Round 2 prompts
   - Add orchestrator node for cross-model comments
   - Update output generator for comment formatting

2. **Round 3 Implementation**
   - Parse targeted questions from Round 2
   - Add routing logic for directed responses
   - Update state management for multi-round flow

3. **Testing**
   - Validate Round 2/3 output format
   - Compare with manual multi-round results

### Phase 3: Advanced Features

1. **Web UI** (Streamlit)
   - Dashboard for experiment execution
   - Real-time progress visualization
   - Interactive result exploration

2. **Result Analysis**
   - Automated response comparison
   - Sentiment analysis
   - Consensus/disagreement detection

3. **Extended Capabilities**
   - Multiple output formats (PDF, JSON, YAML)
   - A/B testing framework
   - Cost optimization strategies

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

---

**Note:** This project is in active development. The automation pipeline is planned but not yet implemented.
