from openai import OpenAI
from google import genai
from google.genai import types
import chess
import json
import requests
import time

GAME_CHANNEL = "chess-battle"
SYSTEM_PROMPT = """You are a grand chess master.
Play the game by submiting fuction calls for the next move.
You will be given the current board as a FEN string and the side you are
playing. The chess_move tool only accepts the legal moves for that
position, so pick one of them. Do not replay the game from the start;
the FEN is the authoritative current position.
"""

## Legal moves are supplied as a tool enum so only valid moves are callable
def params(board: chess.Board) -> dict:
    return {
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
    }

def prompt(board: chess.Board) -> str:
    color = "white" if board.turn == chess.WHITE else "black"
    return f"FEN: {board.fen()}\nYou are playing: {color}"

def report(name, board, elapsed, tokens_in, tokens_out, reasoning):
    color = "white" if board.turn == chess.WHITE else "black"
    print(
        f"move {board.fullmove_number}: {name} ({color}) {elapsed:.1f}s "
    )

## Transmit Player Movements
def publish(channel, message):
    payload = json.dumps(message)
    uri = f'https://h2.pubnubapi.com/publish/demo/demo/0/{channel}/0/{payload}'
    return requests.get(uri).json()

class ChatGPT():
    name = "ChatGPT"
    model = "gpt-5.6-luna"

    def __init__(self):
        self.player = OpenAI()

    def move(self, board: chess.Board) -> dict:
        start = time.time()
        response = self.player.responses.create(
            model=self.model,
            tool_choice={"type": "function", "name": "chess_move"},
            tools=[{
                "type": "function",
                "name": "chess_move",
                "description": "Move piece on chess board.",
                "strict": True,
                "parameters": {**params(board), "additionalProperties": False},
            }],
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt(board)},
            ],
        )
        usage = response.usage
        report(self.name, board, time.time() - start, usage.input_tokens,
               usage.output_tokens, usage.output_tokens_details.reasoning_tokens)

        for item in response.output:
            if item.type == "function_call":
                return json.loads(item.arguments)

class Gemini():
    name = "Gemini"
    model = "gemini-3.6-flash"

    def __init__(self):
        self.player = genai.Client()

    def move(self, board: chess.Board) -> dict:
        start = time.time()
        response = self.player.models.generate_content(
            model=self.model,
            contents=prompt(board),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(function_declarations=[types.FunctionDeclaration(
                    name="chess_move",
                    description="Move piece on chess board.",
                    parameters=params(board),
                )])],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="ANY",
                        allowed_function_names=["chess_move"],
                    ),
                ),
            ),
        )
        usage = response.usage_metadata
        report(self.name, board, time.time() - start, usage.prompt_token_count,
               usage.candidates_token_count, usage.thoughts_token_count)

        for call in response.function_calls or []:
            return dict(call.args)

class Game():
    def __init__(self):
        self.players = {chess.WHITE: ChatGPT(), chess.BLACK: Gemini()}
        self.board = chess.Board()

    def over(self):
        return self.board.is_game_over()

    def winner(self):
        winner = self.board.outcome().winner
        if winner is None:
            return "Draw"
        return f"{self.players[winner].name} wins"

    def move(self):
        uci = self.players[self.board.turn].move(self.board)['move']
        move = chess.Move.from_uci(uci)
        if move not in self.board.legal_moves:
            raise ValueError(f"illegal move {uci} in {self.board.fen()}")

        self.board.push(move)
        return f"{uci[:2]}-{uci[2:]}"

game = Game()
while not game.over():
    publish(GAME_CHANNEL, game.move())

print(f"Game over: {game.board.result()} ({game.board.outcome().termination.name})")
print(game.winner())
