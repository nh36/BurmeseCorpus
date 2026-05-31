from __future__ import annotations

from jbrs_workflow_common import validate_jbrs_workflow


def main() -> None:
    errors = validate_jbrs_workflow()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("JBRS workflow artifacts are valid.")


if __name__ == "__main__":
    main()
