#!/usr/bin/env python3
"""PostToolUse hook: when the session reaches 70% of its context window, tell Claude to run `save`.

Fires once, then re-arms after the context drops (after compaction). Never blocks, never errors out.
The approach follows the continuation plugin's transcript-tail estimate.
"""
import json
import pathlib
import sys
import tempfile

THRESHOLD = 0.70
REARM_BELOW = 0.35
DEFAULT_WINDOW = 200_000
MILLION_MARKERS = ("[1m]", "claude-sonnet-5", "claude-opus-5", "claude-fable-5")
MESSAGE = (
    "This session is about {pct}% full. Run the `save` skill now, quietly, so nothing is lost "
    "when the session compacts. Then carry on with what the user asked."
)


def window_for(model):
    if not model:
        return DEFAULT_WINDOW
    return 1_000_000 if any(m in model for m in MILLION_MARKERS) else DEFAULT_WINDOW


def current_tokens(transcript_path, max_lines=200):
    try:
        lines = _tail_read_lines(transcript_path, max_lines)
    except OSError:
        return None, None
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("message") if isinstance(entry, dict) else None
        if not isinstance(message, dict):
            continue
        model = message.get("model")
        usage = message.get("usage")
        if not model or model == "<synthetic>" or not isinstance(usage, dict):
            continue
        tokens = (usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
                  + usage.get("cache_creation_input_tokens", 0))
        return tokens, model
    return None, None


def _tail_read_lines(transcript_path, max_lines=200, chunk_size=65536):
    """Read the last max_lines from transcript_path by seeking from the end.

    Returns a list of lines (strings). Reads in binary, decodes with errors="replace".
    Raises OSError if file cannot be opened.
    """
    path = pathlib.Path(transcript_path)
    lines = []
    with open(path, 'rb') as f:
        f.seek(0, 2)  # Seek to end
        file_size = f.tell()
        position = file_size
        buffer = b''

        while position > 0 and len(lines) < max_lines:
            # Read a chunk backward
            to_read = min(chunk_size, position)
            position -= to_read
            f.seek(position)
            chunk = f.read(to_read)
            buffer = chunk + buffer

            # Extract complete lines from buffer
            if b'\n' in buffer:
                parts = buffer.split(b'\n')
                # Last part might be incomplete, keep it in buffer
                buffer = parts[0]
                # Add complete lines in reverse order (they came from the end)
                for part in reversed(parts[1:]):
                    if len(lines) < max_lines:
                        lines.append(part.decode(errors='replace'))

    # Don't forget any remaining content in buffer
    if buffer and len(lines) < max_lines:
        lines.append(buffer.decode(errors='replace'))

    return list(reversed(lines))


def decide(tokens, window, armed):
    used = tokens / window
    if armed and used >= THRESHOLD:
        return True, False
    if not armed and used < REARM_BELOW:
        return False, True
    return False, armed


def main(stdin_text, state_dir):
    try:
        data = json.loads(stdin_text)
        session_id = str(data["session_id"])
        transcript = data["transcript_path"]
    except (ValueError, KeyError, TypeError):
        return ""
    tokens, model = current_tokens(transcript)
    if tokens is None:
        return ""
    window = window_for(model)
    state_file = pathlib.Path(state_dir) / f"2nd-brain-ctx-{session_id}"
    armed = not state_file.exists()
    nudge, armed_after = decide(tokens, window, armed)
    try:
        if armed_after:
            state_file.unlink(missing_ok=True)
        else:
            state_file.write_text("nudged")
    except OSError:
        pass
    if not nudge:
        return ""
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": MESSAGE.format(pct=round(100 * tokens / window)),
    }})


if __name__ == "__main__":
    try:
        out = main(sys.stdin.read(), tempfile.gettempdir())
        if out:
            print(out)
    except Exception:
        pass
    sys.exit(0)
