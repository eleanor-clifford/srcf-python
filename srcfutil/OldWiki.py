
def oldwiki():
    """For each /usr/path in sys.path, prepend /opt/path to sys.path if it
    exists."""
    import sys
    from os import path
    pathadd = list()

    for p in sys.path:
        if '/usr' not in p:
            continue
        pp = p.replace('/usr', '/opt')
        if not path.exists(pp):
            continue
        pathadd.append(pp)

    sys.path[:0] = pathadd

