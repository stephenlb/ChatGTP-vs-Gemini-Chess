## TODO GEMINI
from openai import OpenAI
import json

chatgpt = OpenAI()
SYSTEM_PROMPT = """You are a grand chess master.
Play the game by submiting fuction calls for the next move.
You will have the entire state of the board and the previous positions played.
"""

# 1. Define a list of callable tools for the model
tools = [
    {
        "type": "function",
        "name": "chess_move",
        "description": "Move piece on chess board.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "The strategy and reasoning for the movement.",
                },
                "start": {
                    "type": "string",
                    "description": "The starting postiion of the piece to move. Example: 'e2'",
                },
                "end": {
                    "type": "string",
                    "description": "The destination postiion of the piece. Example: 'e4'",
                },
            },
            "required": ["reasoning", "start", "end"],
            "additionalProperties": False
        },
    },
]

# Create a running input list we will add to over time
input_list = [
    {"role": "system", "content": SYSTEM_PROMPT}, 
    {"role": "user", "content": "Game State: "},
]

def game_state(state):
    input_list.append({
        "role": "user",
        "content": f"Game State: {state}",
    })

# 2. Prompt the model with tools defined
response = chatgpt.responses.create(
    model="gpt-5.6",
    tool_choice={"type": "function", "name": "chess_move"},
    tools=tools,
    input=input_list,
)

# Save function call outputs for subsequent requests
input_list += response.output

for item in response.output:
    if item.type == "function_call":
        output = json.loads(item.arguments)
        input_list.append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": output,
        })

print("Final input:")
print(input_list)
