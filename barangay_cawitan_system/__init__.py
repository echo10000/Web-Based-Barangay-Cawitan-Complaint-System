try:
    import pymysql

    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.install_as_MySQLdb()
except ImportError:
    # mysqlclient is the preferred driver. PyMySQL is an optional Windows-friendly fallback.
    pass
