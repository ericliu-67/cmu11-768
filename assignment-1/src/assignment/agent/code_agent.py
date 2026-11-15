"""The Part 1 coding agent: fix a software issue and submit a git patch."""

from __future__ import annotations

import json
from typing import Any

from assignment.agent.base import (
    DEFAULT_COMPACTION_KEEP_RECENT_STEPS,
    DEFAULT_COMPACTION_MAX_TOKENS,
    Agent,
    format_tool_output,
)
from assignment.agent.tools import EXECUTE_TOOL, SEND_MESSAGE_TOOL
from assignment.env import Environment

class CodeAgent(Agent):
    """An agent that fixes a software issue and submits a git patch."""

    def __init__(
        self,
        task: str,
        environment: Environment,
        model: str | None = None,
        logs_save_path: str | None = None,
        step_limit: int = 100,
        skills_path: str | None = None,
        auto_stop_environment: bool = True,
        compact_threshold_tokens: int | None = None,
        compaction_keep_recent_steps: int = DEFAULT_COMPACTION_KEEP_RECENT_STEPS,
        compaction_max_tokens: int = DEFAULT_COMPACTION_MAX_TOKENS,
    ):
        super().__init__(
            environment=environment,
            model=model,
            logs_save_path=logs_save_path,
            step_limit=step_limit,
            skills_path=skills_path,
            auto_stop_environment=auto_stop_environment,
            compact_threshold_tokens=compact_threshold_tokens,
            compaction_keep_recent_steps=compaction_keep_recent_steps,
            compaction_max_tokens=compaction_max_tokens,
        )
        self.task = task
        self.submitted_patch = ""

        # TODO(Part 1.3): Make the `execute` and `send_message` tools available
        # to the agent.
        self.tools.extend([EXECUTE_TOOL, SEND_MESSAGE_TOOL])

        # TODO(1.1.b): Construct the system prompt and task_prompt. These
        # should be usable by the `Agent.build_prompt` method.

        # TODO(1.4): If any skills are available to the agent, make their
        # descriptions/metadata available to the agent in the prompt.
        self.system_prompt = self._build_system_prompt()
        self.task_prompt = self._build_task_prompt()

    def _build_system_prompt(self) -> str:
        system_information = json.dumps(
            {
                "machine": self.env.machine,
                "release": self.env.release,
                "system": self.env.system,
                "version": self.env.version,
            },
            indent=2,
        )
        sections = [
            "You are an autonomous software engineer working in a sandboxed "
            "terminal. You resolve software issues by running commands with the "
            "`execute` tool, reading their output, and iterating.",
            f"<system_information>\n{system_information}\n</system_information>",
            "Guidelines:\n"
            "- Think briefly, then call at least one tool in every response.\n"
            "- Each `execute` call runs in a new subshell: `cd` and `export` do "
            "not persist, so use the `cwd` and `env` arguments instead.\n"
            "- Keep output small: use grep, head, tail, or sed -n to read files.\n"
            "- Reproduce the issue first, then make a minimal fix to the source "
            "code, then re-run the reproduction and the existing tests.\n"
            "- Do not edit existing tests to make them pass.\n"
            "- When you are done, call `send_message` with a summary of your "
            "work. You cannot act after that.",
        ]
        if self.skills:
            catalog = "\n".join(
                f"<skill>\n{skill['metadata']}\n</skill>"
                for skill in self.skills.values()
            )
            sections.append(
                "Skills are reusable workflows written ahead of time. Only their "
                "names and descriptions are listed below; call `invoke_skill` "
                "with a skill's name to read its full instructions before doing "
                "the work it covers.\n"
                f"<available_skills>\n{catalog}\n</available_skills>"
            )
        return "\n\n".join(sections)

    def _build_task_prompt(self) -> str:
        return (
            f"Resolve the following issue in the repository at `{self.env.cwd}`.\n\n"
            f"<issue>\n{self.task}\n</issue>\n\n"
            "Explore the relevant code, reproduce the failure, fix it in the "
            "source files, and verify the fix by re-running your reproduction "
            "and the existing tests."
        )

    
    def execute_tool_calls(
        self, tool_calls: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Execute ``execute`` and ``send_message`` calls in the code sandbox."""
        # 输入是模型一次回复里全部的call 可能有多个即使某条tool坏掉了或没执行 也需要返回一条tool消息 否则下次请求时会因为没有对应的tool消息而报错
        # TODO(Part 1.3): Parse each call, execute recognized tools, and return
        # one message per call (there may be multiple tool calls in one agent
        # response!). Malformed JSON and unknown tools must become recoverable
        # observations relayed to the agent instead of exceptions.
        # tool_calls: list[dict[str, Any]]
        return [
            {
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "content": self._run_tool_call(call),
            }
            for call in tool_calls
        ]

    def _run_tool_call(self, call: dict[str, Any]) -> str:
        function = call.get("function") or {}
        name = function.get("name")

        if self.finished:
            return "<error>Not executed: the task was already submitted with send_message.</error>"

        # 参数通常是 JSON 字符串；模型可能生成坏的 JSON，也可能不是一个对象
        raw_arguments = function.get("arguments") or "{}"
        try: 
            arguments = (
                raw_arguments if isinstance(raw_arguments, dict) else json.loads(raw_arguments)
            )    
        # 解析json失败情形
        except json.JSONDecodeError as error:
            return (
                f"<error>Could not parse arguments for `{name}` as JSON: {error}. "
                "Retry the call with a valid JSON object.</error>"
            )
        
        if not isinstance(arguments, dict):
            return f"<error>Arguments for `{name}` must be a JSON object.</error>"
        
        if name == "execute":
            return self._execute(arguments)
        if name == "send_message":
            return self._send_message(arguments)
        if name == "invoke_skill" and self.skills:
            return self._invoke_skill(arguments)
        available = ", ".join(tool["function"]["name"] for tool in self.tools)
        return f"<error>Unknown tool `{name}`. Available tools: {available}.</error>"

    def _execute(self, arguments: dict[str, Any]) -> str:
        command = arguments.get("command")
        if not command or not isinstance(command, (str, list)):
            return (
                "<error>`execute` requires a non-empty `command` "
                "(a string, or a list of strings).</error>"
            )

        # 只透传模型实际给出的可选参数，其余用 Environment.execute 的默认值
        options = {
            key: arguments[key]
            for key in ("timeout", "cwd", "env", "shell")
            if arguments.get(key) is not None
        }
        return format_tool_output(self.env.execute(command, **options))

    def _send_message(self, arguments: dict[str, Any]) -> str:
        summary = arguments.get("summary")
        if not isinstance(summary, str):
            return "<error>`send_message` requires a string `summary`.</error>"
        self.finished = True
        return "Message sent. The task is complete."
    
    def _invoke_skill(self, arguments: dict[str, Any]) -> str:
        skill_name = arguments.get("name")
        skill = self.skills.get(skill_name) if isinstance(skill_name, str) else None
        if skill is None:
            available = ", ".join(self.skills)
            return (
                f"<error>Unknown skill {skill_name!r}. "
                f"Available skills: {available}.</error>"
            )
        return skill["content"]