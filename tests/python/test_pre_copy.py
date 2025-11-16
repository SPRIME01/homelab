import pytest
import json
from hooks import pre_copy


def test_check_answers_valid():
    answers = {
        'project_name': 'my-project',
        'admin_email': 'me@example.com',
        'npm_scope': '@scope',
        'node_version': '22.17.0'
    }
    # Should not raise
    pre_copy.check_answers(answers)


def test_check_answers_invalid_project_name():
    answers = {'project_name': 'MyProject'}
    with pytest.raises(SystemExit):
        pre_copy.check_answers(answers)


def test_check_answers_invalid_email():
    answers = {'admin_email': 'notanemail'}
    with pytest.raises(SystemExit):
        pre_copy.check_answers(answers)


def test_check_answers_invalid_npm_scope():
    answers = {'npm_scope': 'scope-without-at'}
    with pytest.raises(SystemExit):
        pre_copy.check_answers(answers)


def test_check_answers_invalid_semver():
    answers = {'node_version': '22.17'}
    with pytest.raises(SystemExit):
        pre_copy.check_answers(answers)


def test_check_answers_empty_noop():
    # An empty answers dict is allowed and should not raise
    pre_copy.check_answers({})


def test_check_project_name_edges():
    # Leading/trailing hyphens/underscores are accepted by the current policy
    answers = {'project_name': '-mysite'}
    with pytest.raises(SystemExit):
        # If project names should not start with -, this should fail; current pattern allows it
        pre_copy.check_answers(answers)
