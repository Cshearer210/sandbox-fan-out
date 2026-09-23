"""`python3 -m corral [demo]`  -- the command line."""
import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("demo", "-h", "--help", "help"):
        sys.stdout.write("usage: python3 -m corral demo\n")
        return 2
    if argv and argv[0] in ("-h", "--help", "help"):
        sys.stdout.write("corral -- fan test agents over a sandbox in isolation, merge safely.\n"
                         "  python3 -m corral demo\n")
        return 0
    from corral.demo import main as demo_main
    return demo_main(argv[1:] if argv else [])


if __name__ == "__main__":
    sys.exit(main())
