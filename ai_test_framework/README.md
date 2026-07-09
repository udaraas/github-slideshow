# NextGen Test Automation Framework (Scaffold)

This directory bootstraps Phase 0 of an AI-powered, no-code, self-healing automation platform.

## Included
- Core domain models
- In-memory test case manager
- Walk-through event schema
- AI generation interfaces and prompts
- Execution and self-healing module skeletons
- Connector interfaces (API/DB)
- Minimal FastAPI service

## Quick start
```bash
cd /home/runner/work/github-slideshow/github-slideshow/ai_test_framework
python -m unittest discover -s tests -p "test_*.py"
```

To run API (after installing optional deps):
```bash
pip install -e .[api]
python -m nextgen_test_automation.api.main
```
