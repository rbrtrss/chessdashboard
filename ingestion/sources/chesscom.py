import dlt
from dlt.sources.chess import source as chess_source


def chesscom_games(username: str, max_games: int | None = None):
    """Return dlt Chess.com source configured for the given username."""
    source = chess_source(players=[username])
    if max_games is not None:
        # Limit is applied post-load in the normalizer transformer
        source = source.with_resources("players_games")
    else:
        source = source.with_resources("players_games")
    return source
