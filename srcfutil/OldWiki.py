
def oldwiki():
    """For each /usr/path in sys.path, prepend /opt/path to sys.path if it
    exists."""
    import sys
    from syslog import syslog
    from os import environ, path

    try:
        this = environ['SCRIPT_FILENAME']
    except KeyError:
        this = 'unknown location :('

    syslog('OldWiki handler triggered at ' + this)

    pathadd = list()

    for p in sys.path:
        if '/usr' not in p:
            continue
        pp = p.replace('/usr', '/opt')
        if not path.exists(pp):
            continue
        pathadd.append(pp)

    sys.path[:0] = pathadd
