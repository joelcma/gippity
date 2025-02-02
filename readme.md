# Gippity: A ChatGPT Integration Tool for Code Generation and Automatic File Updates

This project provides a Python script to interact with ChatGPT (OpenAI's  
 language model) for code generation and file updates, integrating with a  
 development workflow.

## Features

• Environment Check: Ensures the OPENAI_API_KEY environment variable is set  
 before execution.  
 • File Handling: Includes functionality for reading file contents from specified
paths and parsing lines from these files.  
 • Logging: Utilizes Python's logging library for detailed information, warnings,
and error logging.  
 • File Updates: Provides automatic file updates based on responses from ChatGPT
using a special format.  
 • Session Continuity: Supports continuing interactions by reading historical  
 data from conversation files.

## Installation

1. Clone the repository:  
   git clone <repository-url>  
   cd <repository-dir>

2. Install required packages:  
   Use pip to install OpenAI and other necessary packages.  
    pip install openai

3. Setup Environment Variable:  
   Ensure your OpenAI API Key is set up as an environment variable.  
    export OPENAI_API_KEY='your-api-key'

## Usage

1. New Session:  
   Start a new conversation with ChatGPT.  
    python gpt.py new "Your message to ChatGPT" [optional file paths]

2. Continue Session:  
   Continue an existing conversation.  
    python gpt.py continue "Your follow-up message to ChatGPT" [optional file
   paths]

3. File Update Automation:  
   Run the script with the --update-files flag to automatically update files  
   based on ChatGPT's suggestions.  
    python gpt.py new "Your message" --update-files

## Important Variables

• MAX_SIZE : Max file size threshold to prevent large file parsing.  
 • DEBUG : Toggles debug mode.  
 • TMP_CONVERSATION_FILE : Path to store conversation history.  
 • TMP_RESPONSE_FILE : Path to store temporary response data from ChatGPT.

## Dependencies

• OpenAI Python API https://pypi.org/project/openai/

## Note

This script is customizable according to your specific requirements. Please  
 refer to the inline comments within the gpt.py script for more detailed  
 implementation logic.

## Contributions & Issues

Contributions are welcome. Please reach out via the repository issues if you  
 encounter a problem or have questions.

---

This README outlines the primary functionality and setup for developers and  
 users interested in integrating ChatGPT with their software development  
 lifecycle efficiently.
