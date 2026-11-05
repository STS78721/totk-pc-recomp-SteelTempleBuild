import sys

if getattr(sys, "frozen", False) and len(sys.argv) == 1:
    # A frozen setup executable opens the visual wizard; source and argument-bearing runs remain the install CLI.
    from installer.modern_gui import main
else:
    from installer.cli import main

sys.exit(main())
