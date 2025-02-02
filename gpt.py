import os
import sys
import logging
import argparse
import re

from openai import OpenAI, RateLimitError, BadRequestError

MAX_SIZE = int(128000 / 8)  # 128 KB per file
DEBUG = False
DEBUG_FILE_UPDATES = False

# File paths
TMP_CONVERSATION_FILE = "/tmp/conversation.txt"
TMP_RESPONSE_FILE = "/tmp/gpt_response.md"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USE_FORMAT = " Provide any suggested file changes with the following format: '<filechange: path/to/file>changes to this file go here</filechange>' so that the answer can be parsed and the files automatically updated"

DEVELOPERS_PREFERRED_TECHNOLOGIES = [
    "Golang",
    "Angular (with bootstrap)",
    "Typescript",
    "Postgresql",
    "NestJS",
    "Python",
]


def check_environment():
    try:
        if "OPENAI_API_KEY" not in os.environ:
            logger.error("OPENAI_API_KEY environment variable is not set.")
            sys.exit(1)
    except KeyError as e:
        logger.error(f"Environment variable error: {e}")
        sys.exit(1)


def get_files_from_path(path):
    if os.path.isfile(path):
        return [path]
    elif os.path.isdir(path):
        return [
            os.path.join(root, file)
            for root, _, filenames in os.walk(path)
            for file in filenames
        ]
    else:
        raise ValueError("Invalid path provided.")


def extract_lines_from_file(file_path, line_range):
    try:
        start_line, end_line = map(int, line_range.split(":"))
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            # Ensure line numbers are within range
            if start_line > 0 and end_line <= len(lines):
                return "".join(lines[start_line - 1 : end_line])  # lines are 0-indexed
            else:
                logger.warning(
                    f"Line range {start_line}:{end_line} out of bounds for file {file_path}."
                )
                return ""
    except (ValueError, IOError) as e:
        logger.error(
            f"Error reading specified lines {line_range} from {file_path}: {e}"
        )
        return ""


def read_files_content_with_lines(paths):
    structured_content = ""
    line_range_pattern = re.compile(r"(.+?)\[(\d+:\d+)\]$")
    for path in paths:
        match = line_range_pattern.match(path)
        if match:
            file_path, line_range = match.groups()
            content = extract_lines_from_file(file_path, line_range)
        else:
            # Fall back to reading the full file if no line range is specified
            try:
                files = get_files_from_path(
                    path.split("[")[0]
                )  # Ignore line range if malformed
                for file_path in files:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if len(content) > MAX_SIZE:
                            logger.warning(f"Skipping {file_path} as it is too large.")
                            continue
                        structured_content += (
                            f"\n<file:{file_path}>\n{content}\n</file>\n"
                        )
                        continue  # continue after each file processed
            except IOError as e:
                logger.warning(f"Skipping {path}: {e}")
                continue
            except ValueError as ve:
                logger.error(ve)
                sys.exit(1)

        if content:
            structured_content += f"\n<file:{file_path}>\n{content}\n</file>\n"
    return structured_content


def pretty_print(file_contents):
    try:
        with open(TMP_RESPONSE_FILE, "w") as f:
            f.write(file_contents)
        os.system(f"glow {TMP_RESPONSE_FILE}")
    finally:
        if os.path.exists(TMP_RESPONSE_FILE):
            os.remove(TMP_RESPONSE_FILE)


def new_message(message, file_content):
    file_content = file_content.strip()
    return (
        f"Message: {message}"
        if not file_content
        else f"Message: {message}\nAttached Files:\n{file_content[:MAX_SIZE]}"
    )


def send_to_chatgpt(history, message):
    divider = "\n\n<NEWEST_MESSAGE>\n" if history else "\n"
    prompt = f"{history}{divider}{message}"

    if DEBUG:
        logger.info("Debug mode is on; returning prompt.")
        return prompt

    check_environment()
    client = OpenAI()

    try:
        content = f"You are a helpful AI assistant who's specialized in software production.{USE_FORMAT}"
        content += f"User's preferred technologies: {DEVELOPERS_PREFERRED_TECHNOLOGIES}"
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": content,
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    except RateLimitError as e:
        logger.error(f"Rate limit exceeded: {e}")
    except BadRequestError as e:
        logger.error(f"Bad request error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

    sys.exit(1)


def create_if_missing(filepath):
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            pass


def write_to_conversation_file(tag, content):
    with open(TMP_CONVERSATION_FILE, "a") as f:
        f.write(f"<{tag}>\n{content}\n</{tag}>\n")


def read_history():
    try:
        with open(TMP_CONVERSATION_FILE, "r") as f:
            return f.read()
    except IOError as e:
        logger.error(f"Error reading conversation history: {e}")
        sys.exit(1)


def parse_response_for_updates(response):
    try:
        updates = {}
        lines = response.split("\n")
        current_file = None
        inside_file_changes = False

        for line in lines:
            if line.startswith("<filechange:"):
                current_file = line[len("<filechange:") :].strip().rstrip(">")
                updates[current_file] = []
                inside_file_changes = True
            elif line.startswith("</filechange>"):
                inside_file_changes = False
            elif inside_file_changes and current_file:
                updates[current_file].append(line)

        for file in updates:
            updates[file] = "\n".join(updates[file])

        logger.info(f"Parsed file updates: {updates}")  # Debugging log

        return updates
    except Exception as e:
        logger.error(f"Error parsing response for updates: {e}")
        return {}


def apply_file_updates(updates):
    for file_path, new_content in updates.items():
        try:
            if DEBUG_FILE_UPDATES:
                logger.info(f"Would have updated file: {file_path}")
                logger.info(f"New content:\n{new_content}")
                continue

            # Comment out the manual confirmation for testing
            # action = input(f"Do you want to update the file: {file_path}? [y/n]: ").strip().lower()
            # if action == "y" or action == "yes" or action == "":

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            logger.info(f"Updated file: {file_path}")

            # else:
            #     logger.info(f"Skipped updating file: {file_path}")

        except IOError as e:
            logger.error(f"Failed to update {file_path}: {e}")


def main():
    global USE_FORMAT
    parser = argparse.ArgumentParser(
        description="Script to interact with ChatGPT and optionally update files."
    )
    parser.add_argument(
        "action",
        choices=["new", "continue"],
        help="Start a new session or continue an existing one",
    )
    parser.add_argument("message", help="Your message to ChatGPT")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Paths to files or directories to include in the message",
    )
    parser.add_argument(
        "--update-files",
        action="store_true",
        help="Automatically apply changes suggested by ChatGPT",
    )

    args = parser.parse_args()

    create_if_missing(TMP_CONVERSATION_FILE)
    previous_chat = ""

    if args.action == "continue":
        previous_chat = read_history()
    else:
        with open(TMP_CONVERSATION_FILE, "w") as f:
            f.write("")

    if not args.update_files:
        USE_FORMAT = ""

    user_message = args.message
    paths = args.paths
    update_files = args.update_files

    file_contents = "\n".join(read_files_content_with_lines([path]) for path in paths)
    message = new_message(user_message, file_contents)
    response = send_to_chatgpt(previous_chat, message)

    write_to_conversation_file("user-question", message)
    write_to_conversation_file("ai-answer", response)

    pretty_print(response)

    if update_files:
        updates = parse_response_for_updates(response)
        apply_file_updates(updates)


if __name__ == "__main__":
    main()
