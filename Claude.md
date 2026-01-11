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

### Completed ✓

- [X] Experiment 3 structure defined
- [X] Manual execution with 4 models (Gemini, Kimi, Claude, ChatGPT)
- [X] Results documented in Blocks A, B, C, and D
- [X] Executive summary generated

### In Progress 🔄

- [ ] Standardizing file structure
- [ ] Documenting experiment methodology

### Planned 📋

- [ ] Automation script development
- [ ] Template extraction system
- [ ] Token calculator utility
- [ ] OpenRouter integration
- [ ] Multi-experiment runner
- [ ] Results analyzer and comparator

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

## Next Steps

1. **Phase 1: Structure**

   - Complete documentation of Experiment 3
   - Create template structure for future experiments
2. **Phase 2: Extraction**

   - Build question/prompt extraction system
   - Create configuration schema for experiments
3. **Phase 3: Automation**

   - Implement LangGraph orchestration
   - Integrate OpenRouter API
   - Add token tracking and cost estimation
4. **Phase 4: Analysis**

   - Develop result aggregation tools
   - Create comparison visualizations
   - Build analysis pipelines

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
