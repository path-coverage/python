"""Rules about a team's members."""


def is_name(name, taken):
    """True for a name of 3 to 19 characters no one has, a chain of three
    over two lines."""
    return (len(name) > 2 and name not in taken
            and len(name) < 20)


def can_edit(member):
    """True for an owner, or an editor whose invite is open: a grouped and
    inside an or."""
    return member.owner or (member.editor and member.invite_open)


def is_led(members):
    """True when some member is an active owner, or there are none: a decision
    inside a generator, inside an or of its own."""
    return any(member.owner and member.active for member in members) or not members
