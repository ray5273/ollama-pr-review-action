# Ollama GitHub Code Review Action

This GitHub Action uses Ollama to automatically perform code reviews on pull requests. It can provide reviews in multiple languages and supports custom models for both code review and translation.

## Features

- Automated code review using Ollama models
- Support for multiple programming languages
- Multilingual review output with translation support
- Risk score assessment (1-5 scale)
- Maintains technical terms in English during translation

## Models

This action uses two types of models:

1. **Review Model** (`MODEL`): The main model used for code review analysis. This model analyzes the code changes and generates technical feedback.
   - Default: `qwen2.5-coder:32b`
   - Example alternatives: `llama3.3`, `deepseek-r1:70b`

2. **Translation Model** (`TRANSLATION_MODEL`): Used specifically for translating the review output to the target language while preserving technical terms.
   - Default: `exaone3.5:32b`
   - Optimized for maintaining technical accuracy during translation

## Recommended Models

### Code Review Models 
- Primary: `qwen2.5-coder:32b` (Recommended)
- Alternative & Lightweight: `qwen2.5-coder:7b`

### Translation Models

1. **Korean Languages**
   - Primary: `exaone3.5:32b` (Recommended)
   - Alternative & Lightweight: `exaone3.5:7.8b`

## Hardware Requirements

### GPU Requirements

This action requires significant computational resources due to the large model sizes:

- **Recommend Requirements**: NVIDIA GPU with 40GB+ VRAM (for 70b and 4-bit quantization models)
  - Required for running large alternative models (llama3.3:70b, deepseek-r1:70b)
  - Combined model size requires approximately 35-40GB VRAM 
  - Recommended AWS Instance: g6e.xlarge (48GB GPU memory)
  - Reference: [AWS G6e Instance Types](https://aws.amazon.com/ko/ec2/instance-types/g6e/)

### Recommended Cloud Instances
1. AWS (Amazon Web Services)
   - Recommend: g6e.xlarge (48GB GPU)
   - Cost-effective alternative: g5.2xlarge (16GB GPU) - for lightweight models only

2. Alternative Setup
   - Use lightweight models (7-8B parameters) on smaller GPUs
   - qwen2.5-coder:7b + exaone3.5:7.8b

## Usage

### Single GPU Server Setup (Recommended)

This example assumes you have a dedicated server with sufficient GPU capacity (48GB+ VRAM) running both the GitHub Action and Ollama server:

```yaml
name: Ollama Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  request-review:
    runs-on: AWS-GPU # Assumes your GPU server is configured as a self-hosted runner

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Run Ollama Code Review
      uses: ./
      with:
        OLLAMA_API_URL: 'http://localhost:11434' # Local Ollama server
        MY_GITHUB_TOKEN: ${{ secrets.MY_GITHUB_TOKEN }}
        OWNER: ${{ github.repository_owner }}
        REPO: ${{ github.event.repository.name }}
        PR_NUMBER: ${{ github.event.pull_request.number }}
        RESPONSE_LANGUAGE: 'Korean'
        MODEL: 'qwen2.5-coder:32b'
        TRANSLATION_MODEL: 'exaone3.5:32b'
```

### Split Setup (Advanced)

For scenarios where you want to run Ollama on a separate GPU server:

1. First, set up your Ollama server on a GPU machine (e.g., AWS g6e.xlarge):
   ```bash
   ollama serve
   ```

2. Then use this workflow on your GitHub Actions:
```yaml
name: Ollama Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  request-review:
    runs-on: ubuntu-latest # Can run on any runner as it only makes API calls

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Run Ollama Code Review
      uses: ./
      with:
        OLLAMA_API_URL: ${{ secrets.OLLAMA_API_URL }} # URL to your GPU server
        MY_GITHUB_TOKEN: ${{ secrets.MY_GITHUB_TOKEN }}
        OWNER: ${{ github.repository_owner }}
        REPO: ${{ github.event.repository.name }}
        PR_NUMBER: ${{ github.event.pull_request.number }}
        RESPONSE_LANGUAGE: 'Korean'
        MODEL: 'qwen2.5-coder:32b'
        TRANSLATION_MODEL: 'exaone3.5:32b'
```

⚠️ **Important Notes:**
- Ensure your Ollama server has sufficient GPU capacity for both models
- The single server setup is recommended for simplicity and security
- For split setup, ensure proper network security between GitHub Actions and your Ollama server
- Configure firewall rules to only allow connections from your GitHub Actions IP ranges

## Configuration

### Required Settings

- `OLLAMA_API_URL`: URL of your Ollama API server
- `MY_GITHUB_TOKEN`: GitHub token with permissions to comment on PRs
- `OWNER`: Repository owner
- `REPO`: Repository name
- `PR_NUMBER`: Pull request number

### Optional Settings

- `CUSTOM_PROMPT`: Additional instructions for the review model
- `RESPONSE_LANGUAGE`: Target language for the review output
- `MODEL`: Ollama model for code review
- `TRANSLATION_MODEL`: Model for translating reviews

## Security

- Ensure your GitHub token has appropriate permissions
- Review models are loaded and unloaded for each review session
- Technical terms are preserved in English during translation

## Requirements

- Python 3.8+
- Ollama server
- Required Python packages:
  - requests>=2.31.0
  - pydantic>=2.10.6

## Local Development

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Set up environment variables
4. Run the script:
```bash
python src/ollama_review.py
```

## Future Improvements
- File-by-file detailed review comments

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
