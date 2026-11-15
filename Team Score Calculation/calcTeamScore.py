"""Calculate SWWU team scores (Sighted, Unsighted, Novice) per TeamSpec.md."""

from itertools import combinations

TEAM_SIZE = 3
SHORT_TEAM_SIZE = 2  # used when a club has no eligible female archer

# Ianseo club code -> club name for the SWWU clubs; archers from any other code or name are excluded.
SWWU_CLUBS = {
    "1077": "Plymouth",
    "1342": "Bath",
    "1373": "Swansea",
    "1380": "Exeter",
    "1759": "Aberystwyth",
    "2373": "Bristol",
    "2490": "Cardiff",
    "2628": "UWE",
}

# name -> (eligibility predicate on an archer dict, max compound archers allowed)
TEAM_DEFS = {
    "Sighted Team": (lambda a: a["division"] in ("R", "C") and a["experience"] in ("E", "N"), 1),
    "Unsighted Team": (lambda a: a["division"] in ("B", "L") and a["experience"] in ("E", "N"), 0),
    "Novice Team": (lambda a: a["division"] in ("R", "B", "L") and a["experience"] == "N", 0),
}


def team_key(members, total_arrows=None):
    """Sort key for a team: higher is better.

    Args:
        members (tuple[dict]): archer dicts in the team.
        total_arrows (int | None): live mode: arrows each archer will shoot in total. Needs an `arrows` count
            (shot so far) per archer. None ranks by total score.
    Returns:
        tuple: (total score, summed tie-break 1, ...), or in live mode (projected score, total score,
            summed tie-break 1, ...) where projected = sum over members of (own average arrow value * total_arrows). Each archer is projected
            on their own average so an archer with few arrows shot cannot dilute the team.
    """
    n_tb = len(members[0]["tiebreaks"])
    total = sum(a["score"] for a in members)
    tiebreaks = tuple(sum(a["tiebreaks"][i] for a in members) for i in range(n_tb))
    if total_arrows:
        return (total_arrows * sum(a["score"] / a["arrows"] for a in members), total, *tiebreaks)
    return (total, *tiebreaks)


def best_team(pool, max_compound, total_arrows=None):
    """Find the highest-scoring valid team from one club's eligible archers.

    Every combination is tested, since taking the top-ranked archers does not guarantee the
    best valid team. Valid = at most `max_compound` compound archers and at least one Female. If the pool has no
    Female, the team is the best SHORT_TEAM_SIZE Open archers instead.

    Args:
        pool (list[dict]): eligible archers for one club and team.
        max_compound (int): maximum compound archers allowed in the team.
        total_arrows (int | None): live mode, choose the team with the best projected score (see `team_key`).
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
            best = max(valid, key=lambda c: team_key(c, total_arrows))
            return tuple(sorted(best, key=lambda a: (a["score"], *a["tiebreaks"]), reverse=True))
    return None


def calculate_teams(archers, total_arrows=None):
    """Compute ranked teams for each team type.

    Args:
        archers (list[dict]): output of `parse_quali_export` or the live parser; archers whose club code and
            name do not match an entry in `SWWU_CLUBS`, or whose score is 0 (did not start), are excluded.
        total_arrows (int | None): live mode: arrows each archer will shoot in total. Archers need an `arrows`
            count; those with no arrows shot are ignored, and teams
            are chosen and ranked by projected score (each archer's own average arrow value * the arrows they will
            shoot in total, summed over the team), so smaller teams rank in the right place.
    Returns:
        dict[str, list[dict]]: team name -> ranked rows. Each row has: rank (int), club (str),
            members (tuple[dict]), score (int), tiebreaks (tuple[int, ...]). Equal scores and
            tie-breaks share a rank (competition ranking: 1, 1, 3). In live mode, rows also hold
            arrows (int, shot so far), average (float) and projected (float).
    """
    archers = [a for a in archers if SWWU_CLUBS.get(a["club_code"], "").lower() == a["club"].lower()]
    archers = [a for a in archers if a["score"] > 0]  # a zero score means the archer did not start
    if total_arrows:
        archers = [a for a in archers if a["arrows"] > 0]
    clubs = sorted({a["club"] for a in archers})
    results = {}
    for team_name, (eligible, max_compound) in TEAM_DEFS.items():
        rows = []
        for club in clubs:
            pool = [a for a in archers if a["club"] == club and eligible(a)]
            members = best_team(pool, max_compound, total_arrows) if pool else None
            if members:
                key = team_key(members, total_arrows)
                row = {"club": club, "members": members, "key": key, "score": sum(a["score"] for a in members)}
                row["tiebreaks"] = key[len(key) - len(members[0]["tiebreaks"]) :]
                if total_arrows:
                    row["arrows"] = sum(a["arrows"] for a in members)
                    row["average"] = key[0] / (total_arrows * len(members))
                    row["projected"] = key[0]
                rows.append(row)
        rows.sort(key=lambda r: r["key"], reverse=True)
        for i, row in enumerate(rows):
            tied = i > 0 and row["key"] == rows[i - 1]["key"]
            row["rank"] = rows[i - 1]["rank"] if tied else i + 1
        results[team_name] = rows
    return results
