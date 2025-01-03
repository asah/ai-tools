import subprocess
import os
import argparse
from anthropic import Anthropic
import openai
import json
from typing import Optional

class DiffAnalyzer:
    def __init__(self, anthropic_api_key: str, openai_api_key: Optional[str] = None):
        self.anthropic = Anthropic(api_key=anthropic_api_key)
        self.openai_api_key = openai_api_key
        if openai_api_key:
            openai.api_key = openai_api_key

    def get_git_diff(self, target: str) -> str:
        """Get git diff excluding package*.json files."""
        try:
            # Get the diff command output
            diff_command = f"git diff {target} -- . ':!package*.json'"
            diff_output = subprocess.check_output(diff_command, shell=True, text=True)
            return diff_output
        except subprocess.CalledProcessError as e:
            print(f"Error getting git diff: {e}")
            return ""

    def analyze_with_claude(self, diff_text: str) -> str:
        """Analyze diff using Claude API."""
        prompt = f"""ignoring the changes that were computer-generated, can you estimate how long this took a human to write this code, assuming they appropriately used AI to help them? please go section by section.

Here's the diff to analyze:
{diff_text}"""

        try:
            response = self.anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Error with Claude API: {e}")
            if self.openai_api_key:
                print("Falling back to ChatGPT...")
                return self.analyze_with_chatgpt(diff_text)
            return f"Error analyzing diff: {e}"

    def analyze_with_chatgpt(self, diff_text: str) -> str:
        """Fallback analysis using ChatGPT API."""
        if not self.openai_api_key:
            return "OpenAI API key not provided for fallback."

        prompt = f"""ignoring the changes that were computer-generated, can you estimate how long this took a human to write this code, assuming they appropriately used AI to help them? please go section by section.

Here's the diff to analyze:
{diff_text}"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error analyzing diff with ChatGPT: {e}"

def main():
    parser = argparse.ArgumentParser(description='Analyze git diffs using AI')
    parser.add_argument('target', help='Git diff target (e.g., HEAD~1)')
    parser.add_argument('--anthropic-key', help='Anthropic API key', default=os.getenv('ANTHROPIC_API_KEY'))
    parser.add_argument('--openai-key', help='OpenAI API key (optional fallback)', default=os.getenv('OPENAI_API_KEY'))
    args = parser.parse_args()

    if not args.anthropic_key:
        print("Error: Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable or use --anthropic-key")
        return

    analyzer = DiffAnalyzer(args.anthropic_key, args.openai_key)
    
    # Get the diff
    diff_text = analyzer.get_git_diff(args.target)
    if not diff_text:
        print("No diff found or error occurred")
        return

    # Analyze the diff
    analysis = analyzer.analyze_with_claude(diff_text)
    print("\nAnalysis Results:")
    print("----------------")
    print(analysis)

if __name__ == "__main__":
    main()
