from optimizer import optimize_strategy

def test_optimize_strategy_bahrain():
    res = optimize_strategy(track_id="bahrain", max_stops=2)
    assert "optimal_strategy" in res
    assert "expected_time" in res
    assert "top_5_alternatives" in res
    
    # ensure multiple dry compounds are used in optimal strategy
    stints = res["optimal_strategy"]
    assert len(stints) > 0
    unique_compounds = set(s["compound"] for s in stints)
    dry_compounds_used = unique_compounds - {"intermediate", "wet"}
    assert len(dry_compounds_used) >= 2
