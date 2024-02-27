"""Run all the examples to check for errors."""


import importlib
import sys
import os
import pytest


class TestExamples:

    @pytest.mark.parametrize("example_file_sans_extension", [
        "change_word_cases",
        "branching_cases_long_declarations",
        "branching_cases_wrapped_declarations",
    ])
    def test_run_synchronous_examples(self, example_file_sans_extension, capsys):
        # Add the project directory to sys.path to allow importing modules
        project_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(project_dir)

        module_name = "examples." + example_file_sans_extension
        example_module = importlib.import_module(module_name)
        try:
            _ = example_module.main()
        except Exception as e:
            error_message = f"Error in example {example_file_sans_extension}: {e}"
            print(error_message, file=sys.stderr)
            assert False, error_message

        captured = capsys.readouterr()
        assert not captured.err, f"Error captured in stderr: {captured.err}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("example_file_sans_extension", [
        "async_word_cases",
    ])
    async def test_run_asynchronous_examples(self, example_file_sans_extension, capsys):
        # Add the project directory to sys.path to allow importing modules
        project_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(project_dir)

        module_name = "examples." + example_file_sans_extension
        example_module = importlib.import_module(module_name)
        try:
            _ = await example_module.main()
        except Exception as e:
            error_message = f"Error in example {example_file_sans_extension}: {e}"
            print(error_message, file=sys.stderr)
            assert False, error_message

        captured = capsys.readouterr()
        assert not captured.err, f"Error captured in stderr: {captured.err}"
