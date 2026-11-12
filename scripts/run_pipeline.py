"""Run every data and ranking phase in the project virtual environment."""

from build_cumulative_dataset import build, DEFAULT_INPUT, DEFAULT_OUTPUT
from build_match_state import main as build_match_state
from label_pressure import main as label_pressure
from build_context import main as build_context
from build_win_probability import main as build_win_probability
from compare_exact_scores import main as compare_exact_scores
from import_cricsheet_extras import DEFAULT_EXTRAS
from score_players import main as score_players
from profile_context import main as profile_context
from rank_elite_matchups import main as rank_elite_matchups
from validate_pipeline import main as validate_pipeline
from check_robustness import main as check_robustness


def main() -> None:
    build(DEFAULT_INPUT, DEFAULT_OUTPUT)
    build_match_state()
    label_pressure()
    build_context()
    build_win_probability()
    if not DEFAULT_EXTRAS.is_file():
        raise FileNotFoundError(f"Verified Cricsheet extras cache missing: {DEFAULT_EXTRAS}")
    build_win_probability(exact_only=True)
    compare_exact_scores()
    score_players()
    profile_context()
    rank_elite_matchups()
    validate_pipeline()
    check_robustness()


if __name__ == "__main__":
    main()
