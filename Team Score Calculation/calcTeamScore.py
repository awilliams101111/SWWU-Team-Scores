"""Calculate SWWU team scores (Sighted, Unsighted, Novice) per TeamSpec.md."""

from itertools import combinations

TEAM_SIZE = 3
SHORT_TEAM_SIZE = 2  # used when a club has no eligible female archer

# name -> (eligibility predicate on an archer dict, max compound archers allowed)
TEAM_DEFS = {
    "Sighted Team": (lambda a: a["division"] in ("R", "C") and a["experience"] in ("E", "N"), 1),
    "Unsighted Team": (lambda a: a["division"] in ("B", "L") and a["experience"] in ("E", "N"), 0),
    "Novice Team": (lambda a: a["division"] in ("R", "B", "L") and a["experience"] == "N", 0),
}


def team_key(members):
    """Sort key for a team: higher is better.

    Args:
        members (tuple[dict]): archer dicts in the team.
    Returns:
        tuple[int, ...]: (total score, summed tie-break 1, summed tie-break 2, ...).
    """
    n_tb = len(members[0]["tiebreaks"])
    return (sum(a["score"] for a in members), *(sum(a["tiebreaks"][i] for a in members) for i in range(n_tb)))


def best_team(pool, max_compound):
    """Find the highest-scoring valid team from one club's eligible archers.

    Every combination is tested, since taking the top-ranked archers does not guarantee the
    best valid team. Valid = at most `max_compound` compound archers and at least one Female. If the pool has no
    Female, the team is the best SHORT_TEAM_SIZE Open archers instead.

    Args:
        pool (list[dict]): eligible archers for one club and team.
        max_compound (int): maximum compound archers allowed in the team.
    Returns:
        tuple[dict] | None: best team ordered by score descending, or None if no archers.
    """
    has_female = any(a["gender"] == "F" for a in pool)
    size = TEAM_SIZE if has_female else SHORT_TEAM_SIZE
    for k in range(min(size, len(pool)), 0, -1):
        valid = [
            c for c in combinations(pool, k)
            if sum(a["division"] == "C" for a in c) <= max_compound
            and (not has_female or any(a["gender"] == "F" for a in c))
        ]
        if valid:
            best = max(valid, key=team_key)
            return tuple(sorted(best, key=lambda a: (a["score"], *a["tiebreaks"]), reverse=True))
    return None


def calculate_teams(archers):
    """Compute ranked teams for each team type.

    Args:
        archers (list[dict]): output of `parse_quali_export`.
    Returns:
        dict[str, list[dict]]: team name -> ranked rows. Each row has: rank (int), club (str),
            members (tuple[dict]), score (int), tiebreaks (tuple[int, ...]). Equal scores and
            tie-breaks share a rank (competition ranking: 1, 1, 3).
    """
    clubs = sorted({a["club"] for a in archers})
    results = {}
    for team_name, (eligible, max_compound) in TEAM_DEFS.items():
        rows = []
        for club in clubs:
            pool = [a for a in archers if a["club"] == club and eligible(a)]
            members = best_team(pool, max_compound) if pool else None
            if members:
                key = team_key(members)
                rows.append({"club": club, "members": members, "score": key[0], "tiebreaks": key[1:]})
        rows.sort(key=lambda r: (r["score"], *r["tiebreaks"]), reverse=True)
        for i, row in enumerate(rows):
            tied = i > 0 and (row["score"], row["tiebreaks"]) == (rows[i - 1]["score"], rows[i - 1]["tiebreaks"])
            row["rank"] = rows[i - 1]["rank"] if tied else i + 1
        results[team_name] = rows
    return results
