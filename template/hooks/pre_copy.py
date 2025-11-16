#!/usr/bin/env python3
"""
Pre-copy validation hook for Copier template.
This will be included in the template's `hooks/` directory so Copier can run it from the generated project.
"""
import argparse
import json
import re
import sys


def die(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def is_semver(v: str) -> bool:
    return bool(re.match(r"^\d+\.\d+\.\d+$", v))


def is_npm_scope(v: str) -> bool:
    if not v:
        return True
    return bool(re.match(r"^@[a-z0-9\-_]+$", v))


def is_project_name_valid(name: str) -> bool:
    return bool(re.match(r"^[a-z0-9\-_]+$", name))


def is_valid_email(v: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v))


def check_answers(answers: dict):
    # Basic validations
    if 'project_name' in answers and not is_project_name_valid(answers.get('project_name', '')):
        die(f"project_name must be lowercase alnum plus '-' and '_'. Got: {answers.get('project_name')}")

    if 'admin_email' in answers and not is_valid_email(answers.get('admin_email', '')):
        die(f"admin_email appears invalid: {answers.get('admin_email')}")

    if 'npm_scope' in answers and not is_npm_scope(answers.get('npm_scope', '')):
        die(f"npm_scope must be empty or start with @ and contain lowercase alphanumerics or -/_; got: {answers.get('npm_scope')}")

    for tf in ('node_version','python_version','pulumi_version','pnpm_version','nx_version'):
        v = answers.get(tf)
        if v and not is_semver(v):
            die(f"{tf} must be semver x.y.z; got: {v}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full-conf', type=str)
    parser.add_argument('--answers', type=str)
    args = parser.parse_args()

    answers = {}
    if args.answers:
        try:
            answers = json.loads(args.answers)
        except Exception as e:
            die(f"Failed parsing --answers as JSON: {e}")

    check_answers(answers)
    print("pre_copy validation: OK")


if __name__ == '__main__':
    main()
