# Folio

Generate a spectacular GitHub profile page from your local machine.

## What Is This?

Folio is a CLI tool that builds your GitHub profile page. This repo **is** your profile repo — fork it, configure it, run `folio generate`, and push. Your README.md and a full HTML profile site are generated from your GitHub data and AI-powered summaries.

## Quick Start

1. Fork this repo and rename it to `yourusername/yourusername`
2. Clone it locally
3. Install: `pip install -e .`
4. Run the setup wizard: `folio init`
5. Edit `.profile.yml` to add your repos
6. Generate your profile: `folio generate`
7. Push: `git push`
8. (Optional) Enable GitHub Pages on the repo for the full HTML site

## Commands

| Command | What it does |
|---|---|
| `folio init` | Interactive setup wizard — creates `.profile.yml` |
| `folio generate` | Fetch GitHub data, run AI summaries, write README.md and dist/ |
| `folio preview` | Serve the generated HTML site locally |
| `folio status` | Show what would change without generating |
| `folio cache clear` | Clear the AI summary cache |

### Flags

| Flag | Description |
|---|---|
| `--config PATH` | Custom config file path (default: `.profile.yml`) |
| `--no-ai` | Skip AI summarization |
| `--push` | Commit and push after generating |
| `--verbose` | Detailed progress output |
| `--theme THEME` | Override the theme (dark/light/auto) |

## Configuration

Copy `.profile.yml.example` to `.profile.yml` and customize. The config file is gitignored — it contains your personal preferences and is never committed.

See `.profile.yml.example` for all options and documentation.

## AI Providers

Folio uses [LiteLLM](https://github.com/BerriAI/litellm) to support multiple AI providers. Set your provider and model in `.profile.yml`, and your API key as an environment variable:

- **Anthropic**: `export ANTHROPIC_API_KEY=sk-ant-...`
- **OpenAI**: `export OPENAI_API_KEY=sk-...`
- **OpenRouter**: `export OPENROUTER_API_KEY=sk-or-...`
- **Ollama**: No key needed — set `base_url` to your Ollama instance

## How Repos Work

- **Public repos** show a summary and a link to GitHub
- **Private repos** show a summary and a reason (e.g. "Under NDA") — no link
- **Forks** show what the upstream project does and what you changed
- All repos are opt-in via the `include` list (or default to all public repos)
- Use `exclude` to hide specific repos

## License

MIT
