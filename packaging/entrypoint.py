"""Official windowless entry point. No CLI, test hooks or runtime installation."""
from desktop.launcher import main

if __name__ == '__main__':
    raise SystemExit(main())
