#!/usr/bin/env python3
"""Claude Code hook → 写桌宠状态到 .pet_state 文件"""
import sys, os, json, time, fnmatch

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pet_state")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")

TOOL_ANIM = {
    "Write": "writing", "Edit": "writing", "NotebookEdit": "writing",
    "Read": "reading", "Grep": "reading", "Glob": "reading",
    "WebFetch": "reading", "WebSearch": "reading",
    "Bash": "running", "PowerShell": "running",
    "Agent": "running", "Workflow": "running",
}

def get_message(tool, inp):
    """从 tool_input 提取简要信息用于气泡显示"""
    if not inp:
        return ""
    if tool in ("Bash", "PowerShell"):
        cmd = inp.get("command", "")
        return cmd[:40] + "..." if len(cmd) > 40 else cmd
    if tool in ("Read",):
        return inp.get("file_path", "").split("/")[-1].split("\\")[-1]
    if tool in ("Write", "Edit"):
        return inp.get("file_path", "").split("/")[-1].split("\\")[-1]
    if tool in ("Grep", "Glob"):
        return inp.get("pattern", "")[:30]
    if tool == "WebFetch":
        return inp.get("url", "")[:40]
    if tool == "WebSearch":
        return inp.get("query", "")[:30]
    return tool

def load_allowed_patterns():
    """从 settings.json 读取已授权的 Bash 命令模式"""
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
        allow_list = settings.get("permissions", {}).get("allow", [])
        patterns = []
        for item in allow_list:
            if "(" in item and item.endswith(")"):
                tool = item.split("(")[0]
                pattern = item[len(tool)+1:-1]
                patterns.append((tool, pattern))
        return patterns
    except:
        return []

def needs_permission(tool_name, tool_input, allowed):
    """判断工具是否需要权限确认"""
    if tool_name not in TOOL_ANIM:
        return True
    if tool_name in ("Bash", "PowerShell"):
        cmd = tool_input.get("command", "")
        for t, pattern in allowed:
            if t == tool_name and fnmatch.fnmatch(cmd, pattern):
                return False
        return True
    return False

def write_state(state, detail="", message=""):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"state": state, "detail": detail, "message": message, "ts": time.time()}, f)
    except:
        pass

def main():
    raw = ""
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except:
        data = {}

    hook_event = data.get("hook_event_name", "") or data.get("event", "") or data.get("type", "")
    tool_name = data.get("tool_name", "") or data.get("tool", "")

    if not hook_event:
        for key in ["CLAUDE_HOOK_EVENT", "CLAUDE_EVENT", "CLAUDE_HOOK_TYPE"]:
            hook_event = os.environ.get(key, "")
            if hook_event:
                break

    tool_input = data.get("tool_input", {})

    if "PreToolUse" in hook_event:
        allowed = load_allowed_patterns()
        if needs_permission(tool_name, tool_input, allowed):
            # 需要权限确认 → 感叹号
            write_state("waiting", tool_name, "❗")
        else:
            # 正常执行 → 显示工具信息
            anim = TOOL_ANIM.get(tool_name, "waiting")
            msg = get_message(tool_name, tool_input)
            write_state(anim, tool_name, msg)
    elif "PostToolUse" in hook_event:
        write_state("idle")
    elif "Stop" in hook_event:
        write_state("wave", "finished", "finished")
    else:
        write_state("idle")

if __name__ == "__main__":
    main()
