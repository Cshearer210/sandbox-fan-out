"""`python3 -m corral [demo|scoreboard <out_dir>]`  -- the command line."""
import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "scoreboard":
        from corral.scoreboard import main as run
        return run(argv[1:])
    if argv and argv[0] in ("-h", "--help", "help"):
        sys.stdout.write("corral -- fan test agents over a sandbox in isolation, merge safely.\n"
                         "  python3 -m corral demo\n"
                         "  python3 -m corral scoreboard <out_dir>   # classified tally of a fan-out run\n")
        return 0
    if argv and argv[0] not in ("demo",):
        sys.stdout.write("usage: python3 -m corral [demo|scoreboard <out_dir>]\n")
        return 2
    from corral.demo import main as demo_main
    return demo_main(argv[1:] if argv else [])


if __name__ == "__main__":
    sys.exit(main())
