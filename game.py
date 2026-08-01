from openai import OpenAI
from google import genai
from google.genai import types
import chess
import json
import requests
import time

#gpt-5.6-luna
#gemini-3.6-flash

GAME_CHANNEL = "chess-battle"
SYSTEM_PROMPT = """You are a grand chess master.
Play the game by submiting fuction calls for the next move.
You will be given the current board as a FEN string and the side you are
playing. The chess_move tool only accepts the legal moves for that
position, so pick one of them. Do not replay the game from the start;
the FEN is the authoritative current position.
"""

## Legal moves are supplied as a tool enum so only valid moves are callable
def tools(board: chess.Board) -> list:
    return [{
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
                "move": {
                    "type": "string",
                    "description": "The legal move in UCI notation. Example: 'e2e4'",
                    "enum": [m.uci() for m in board.legal_moves],
                },
            },
            "required": ["reasoning", "move"],
            "additionalProperties": False
        },
    }]

## Transmit Player Movements
def publish(channel, message):
    origin = 'https://h2.pubnubapi.com'
    pubkey = 'demo'
    subkey = 'demo'
    payload = json.dumps(message)
    uri = f'{origin}/publish/{pubkey}/{subkey}/0/{channel}/0/{payload}'
    response = requests.get(uri)
    return response.json()

class Player():
    def move(self, board: chess.Board) -> str:
        pass

class ChatGPT(Player):
    def __init__(self):
        self.player = OpenAI()

    def chat(self, board: chess.Board):
        color = "white" if board.turn == chess.WHITE else "black"
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"FEN: {board.fen()}\n"
                f"You are playing: {color}"
            )},
        ]

    def move(self, board: chess.Board) -> str:
        start_time = time.time()
        response = self.player.responses.create(
            model="gpt-5.6-luna",
            tool_choice={"type": "function", "name": "chess_move"},
            tools=tools(board),
            input=self.chat(board),
        )
        elapsed = time.time() - start_time

        usage = response.usage
        reasoning = usage.output_tokens_details.reasoning_tokens
        print(
            f"move {board.fullmove_number}: {elapsed:.1f}s "
            f"in={usage.input_tokens} "
            f"out={usage.output_tokens} "
            f"reasoning={reasoning}"
        )

        for item in response.output:
            if item.type == "function_call":
                output = json.loads(item.arguments)
                return output

class Gemini(Player):
    def __init__(self):
        self.player = genai.Client()

    ## Legal moves are supplied as a tool enum so only valid moves are callable
    def config(self, board: chess.Board) -> types.GenerateContentConfig:
        chess_move = types.FunctionDeclaration(
            name="chess_move",
            description="Move piece on chess board.",
            parameters={
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "The strategy and reasoning for the movement.",
                    },
                    "move": {
                        "type": "string",
                        "description": "The legal move in UCI notation. Example: 'e2e4'",
                        "enum": [m.uci() for m in board.legal_moves],
                    },
                },
                "required": ["reasoning", "move"],
            },
        )

        return types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=[chess_move])],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="ANY",
                    allowed_function_names=["chess_move"],
                ),
            ),
        )

    def contents(self, board: chess.Board) -> list:
        color = "white" if board.turn == chess.WHITE else "black"
        return [
            types.Content(role="user", parts=[types.Part(text=(
                f"FEN: {board.fen()}\n"
                f"You are playing: {color}"
            ))]),
        ]

    def move(self, board: chess.Board) -> str:
        start_time = time.time()
        response = self.player.models.generate_content(
            model="gemini-3.6-flash",
            contents=self.contents(board),
            config=self.config(board),
        )
        elapsed = time.time() - start_time

        usage = response.usage_metadata
        reasoning = usage.thoughts_token_count or 0
        print(
            f"move {board.fullmove_number}: {elapsed:.1f}s "
            f"in={usage.prompt_token_count} "
            f"out={usage.candidates_token_count} "
            f"reasoning={reasoning}"
        )

        for call in response.function_calls or []:
            return dict(call.args)

class Game():
    def __init__(self):
        self.player1_chatgpt = ChatGPT()
        self.player2_gemini = Gemini()
        self.board = chess.Board()

    def transmit(self, move):
        return publish(GAME_CHANNEL, move)

    def over(self):
        return self.board.is_game_over()

    def move(self):
        if self.board.turn == chess.WHITE:
            player = self.player1_chatgpt
        else:
            player = self.player2_gemini

        output = player.move(self.board)
        uci = output['move']
        move = f"{uci[:2]}-{uci[2:]}"

        candidate = chess.Move.from_uci(uci)
        if candidate not in self.board.legal_moves:
            raise ValueError(f"illegal move {move} in {self.board.fen()}")

        self.board.push(candidate)
        return move

game = Game()
while not game.over():
    move = game.move()
    game.transmit(move)

print(f"Game over: {game.board.result()} ({game.board.outcome().termination.name})")
