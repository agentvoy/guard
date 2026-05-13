# agentvoy-guard

Runtime guardrails enforcement for AI agents. Reads `agent.guard.yml` and enforces limits at execution time.

```bash
pip install agentvoy-guard
```

## What it enforces

| Guardrail | Config key | What happens |
|-----------|-----------|--------------|
| Iteration limit | `guardrails.behavior.max_iterations` | Raises `IterationLimitError` |
| Tool call limit | `guardrails.behavior.max_tool_calls` | Raises `ToolCallLimitError` |
| Cost limit | `guardrails.behavior.cost_limit` | Raises `CostLimitError` |
| Timeout | `guardrails.behavior.timeout` | Raises `TimeoutError` |
| Prompt injection | `guardrails.input.block_prompt_injection` | Raises `PromptInjectionError` |
| PII detection | `guardrails.input.pii_detection` | Warns or raises `PIIDetectedError` |
| Network access | `permissions.network` | Patches urllib/requests/httpx |
| Shell execution | `permissions.execution.allow_shell` | Patches os.system |
| Subprocess | `permissions.execution.allow_subprocess` | Patches subprocess |

## Quick start

```python
from agentvoy_guard import Guard

# Loads agent.guard.yml automatically from current directory
guard = Guard.from_config()

with guard.session() as session:
    # Check user input before passing to agent
    session.check_input(user_prompt)

    for i in range(100):
        session.tick()                        # enforces max_iterations + timeout

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            messages=messages,
            tools=tools,
        )

        session.track_usage(response.usage)   # enforces cost_limit

        if response.stop_reason == "tool_use":
            session.tick_tool()               # enforces max_tool_calls

        elif response.stop_reason == "end_turn":
            break

    session.check_output(final_text)

print(guard.last_summary)
# {'iterations': 3, 'tool_calls': 2, 'elapsed_seconds': 4.1,
#  'input_tokens': 1240, 'output_tokens': 380, 'estimated_cost_usd': 0.000952}
```

## Decorator usage

```python
@guard.protect
def run_agent(prompt: str) -> str:
    # input checked automatically, output checked on return
    ...
```

## agent.guard.yml reference

```yaml
version: "1.0"

model:
  provider: anthropic
  model: claude-sonnet-4-20250514

permissions:
  network:
    mode: restricted          # open | restricted | disabled
    allow: ["*.github.com"]
    deny: ["*.social-media.com"]
  execution:
    allow_shell: false
    allow_subprocess: false

guardrails:
  input:
    block_prompt_injection: true
    pii_detection: warn        # off | warn | block
    max_tokens: 4096
  behavior:
    max_iterations: 20
    max_tool_calls: 50
    timeout: 5m
    cost_limit: "$1.00"
```

## Supported model pricing

Token costs are tracked for: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `o1`, `claude-opus-4`, `claude-sonnet-4`, `claude-haiku-4`, `gemini-2.0-flash`, `gemini-2.5-pro`, `llama-3.3-70b`, `mistral-large`.

## Part of AgentVoy

`agentvoy-guard` is part of the [AgentVoy](https://agentvoy.com) platform — the universal AI agent development platform.

```bash
npx agentvoy create my-agent   # scaffolds agent.guard.yml automatically
```

## License

Apache 2.0
