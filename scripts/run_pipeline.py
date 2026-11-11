"""Run every data and ranking phase in the project virtual environment."""

from build_cumulative_dataset import build, DEFAULT_INPUT, DEFAULT_OUTPUT
from build_match_state import main as build_match_state
from label_pressure import main as label_pressure
from build_context import main as build_context
from score_players import main as score_players
from validate_pipeline import main as validate_pipeline
from check_robustness import main as check_robustness


def main() -> None:
    build(DEFAULT_INPUT, DEFAULT_OUTPUT)
    build_match_state()
    label_pressure()
    build_context()
    score_players()
    validate_pipeline()
    check_robustness()


if __name__ == "__main__":
    main()
