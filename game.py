## TODO GEMINI
from openai import OpenAI
import json

#gpt-5.6-terra
#gemini-3.6-flash

SYSTEM_PROMPT = """You are a grand chess master.
Play the game by submiting fuction calls for the next move.
You will have the entire state of the board and the previous positions played.
"""
TOOLS = [
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

class Player():
    def move(self, history: list) -> str:
        pass

class ChatGPT(Player):
    def __init__(self):
        self.player = OpenAI()

    def chat(self, game_state=['start']):
        history = "\n".join(game_state)
        return [
            {"role": "system", "content": SYSTEM_PROMPT}, 
            {"role": "user", "content": f"Game History: {history} "},
        ]

    def move(self, history: list) -> str:
        response = self.player.responses.create(
            model="gpt-5.6",
            tool_choice={"type": "function", "name": "chess_move"},
            tools=TOOLS,
            input=self.chat(history),
        )

        for item in response.output:
            if item.type == "function_call":
                output = json.loads(item.arguments)
                return output

"""
class Gemini(Player):
    def __init__(self):
        pass
    def move(self, history: list) -> str:
        pass
    
    def __init__(self):
        self.player1_chatgpt = OpenAI()
        self.player2_gemini = None
        self.history = []

    def tranmit_move(self, move):
        pass

    def next_move(self):
        if len(self.history) % 2 == 0:
            player = self.player1_chatgpt
        else:
            ## TODO
            player = self.player1_chatgpt
            #player = self.player2_gemini
"""

class Game():
    def __init__(self):
        self.player1_chatgpt = ChatGPT()
        self.player2_gemini = None
        self.history = []

    def transmit(self, move):
        pass

    def move(self):
        if len(self.history) % 2 == 0:
            player = self.player1_chatgpt
        else:
            ## TODO
            player = self.player1_chatgpt
            #player = self.player2_gemini

        ## TODO self.history
        output = player.move(self.history)
        move = f"{output['start']}-{output['end']}"
        self.history.append(move)
        print(move)
        print(output)

game = Game()
while True: ## While Game not over
    game.move()

