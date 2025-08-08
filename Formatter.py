def parse_duration(duration) -> str:
    """

    :param:
    :return:
    """
    prefix = "-" if duration[0] == "-" else "+"
    duration = duration.removeprefix(prefix)

    if duration.startswith("00:"):
        duration = duration[3:duration.index(".")]
    return prefix + duration
