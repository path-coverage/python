from path_coverage import manifest, page_cards, site_paths


def test_7d61a401():
    """Example: size, a match whose second case is guarded, case count if
    count > 10, no path taken
    The guarded case is a condition nested in the match, its pattern then
    its guard, so its fold row is placed at its code, from its pattern to
    its guard's end, as every other row of a fold is."""
    source = (
        "def size(n):\n"
        "    match n:\n"
        "        case 0:\n"
        '            return "none"\n'
        "        case count if count > 10:\n"
        '            return "many"\n'
    )
    sites = manifest.sites(source, "k.py")
    site = "k.py:2:4"
    paths = {site: [{"path": path, "count": 0} for path in site_paths.possible(sites[site])]}
    rows = page_cards.folds(source, sites, paths)(site, "match")
    [case] = [row for row in rows if row["kind"] == "subtree"]
    assert [case["label"]["text"], case["at"]] == ["case", [5, 13, 5, 32]]
