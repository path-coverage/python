"""What the reports say about each site's paths beyond their counts, worked
out from each covered file's source: where each leaf is, and what it says."""


def of(paths, files):
    """{site: {"leaves": [...], "taken": [...]}}: taken is each path and its
    count, as result.paths gives them, and leaves each leaf's
    ["line:col", "line:col"] span, so a tool can recover each leaf exactly.
    files is {path: (source, sites)}."""
    spans = _each_site(files, _spans)
    return {site: {"leaves": spans[site], "taken": taken} for site, taken in paths.items()}


def texts(files):
    """{site: [each leaf's source text]} for every site in files."""
    return _each_site(files, lambda source, leaf: _segment(source, leaf))


def _each_site(files, of_leaf):
    """{site: [of_leaf(source, leaf) for each leaf]} for every site in
    files."""
    return {
        site: [of_leaf(source, leaf) for leaf in condition.leaves()]
        for source, sites in files.values()
        for site, condition in sites.items()
    }


def _spans(source, leaf):
    """leaf's ["line:col", "line:col"], each column counted in characters
    from 0, as site names count them."""
    return [_at(source, leaf.line, leaf.col), _at(source, leaf.end_line, leaf.end_col)]


def _at(source, line, byte_col):
    """"line:col" of the byte column byte_col of line in source."""
    text = source.encode().splitlines(keepends=True)[line - 1]
    return f"{line}:{len(text[:byte_col].decode())}"


def _segment(source, leaf):
    """The source text leaf spans, which may run over several lines."""
    return segment(source, leaf.line, leaf.col, leaf.end_line, leaf.end_col)


def segment(source, line, col, end_line, end_col):
    """The source text from line, col to end_line, end_col, lines counted
    from 1 and columns in UTF-8 bytes from 0, as ast counts them."""
    lines = source.encode().splitlines(keepends=True)
    if line == end_line:
        return lines[line - 1][col:end_col].decode()
    parts = [lines[line - 1][col:], *lines[line : end_line - 1], lines[end_line - 1][:end_col]]
    return b"".join(parts).decode()
