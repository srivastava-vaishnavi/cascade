from importlib.metadata import version

def main() -> int:
    __version__ = version("cascade")
    print(__version__)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())