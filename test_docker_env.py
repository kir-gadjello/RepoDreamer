import os
import pytest
from docker_env import DockerEnv

@pytest.fixture
def docker_env():
    return DockerEnv()

def test_copy_and_run_python_file(docker_env):
    # Create a sample Python file
    python_code = "print('Hello, World!')"
    python_file = "test_python.py"

    # Write the Python code to a temporary file
    with open(python_file, "w") as f:
        f.write(python_code)

    # Copy the Python file into the Docker environment
    docker_env.copy_files([python_file])

    # Run the Python file in the Docker environment
    result, code = docker_env.run_command(f"python {python_file}")

    # Check that the output is correct
    assert code == 0 and result.strip() == "Hello, World!"

    # Clean up
    os.remove(python_file)