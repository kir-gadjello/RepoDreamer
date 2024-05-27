import docker
import os
import tarfile
import io
import time
import json

class DockerEnv:
    def __init__(self, image="python:3.11.9-bookworm", project_dir="/project", verbose=False):
        self.verbose = verbose
        self.client = docker.from_env()
        self.container = None
        self.project_dir = project_dir
        self.image = image
        self.start()

    def start(self):
        self.container = self.client.containers.run(self.image, detach=True, tty=True)
        self.ensure_container_running()
        self.run_command(f"mkdir -p {self.project_dir}")

    def ensure_container_running(self, timeout=5):
        t0 = time.time()
        max_wait = 0.2
        dt = 0.01
        container = self.container
        if container.status != "running":
            container.start()
            while container.status != "running":
                container.reload()
                time.sleep(dt)
                dt = min(max_wait, dt * 2)
                if time.time() - t0 > timeout:
                    raise Exception("docker container start timeout exceeded")
            if self.verbose:
                print(
                    f"container started @{round(time.time() - t0, 2)}s:",
                    container.status,
                    json.dumps(json.loads(next(container.stats()).decode("utf-8")), indent=2),
                )

    def restart(self):
        if self.container.status == "running":
            self.restart()
            self.ensure_container_running()
        else:
            self.container.remove(force=True)
            self.start()

    def copy_files(self, file_paths=[], file_dict=None, dst=None):
        """Copy files into the container"""
        if self.verbose:
            print("ISOLATE: input file_paths={file_paths}, file_dict={file_dict.keys()}")
        
        tar_stream = io.BytesIO()
        with tarfile.TarFile(fileobj=tar_stream, mode="w") as tar:
            for file in file_paths:
                tar.add(file)
            
            if file_dict:
                for file_path, file_content in file_dict.items():
                    info = tarfile.TarInfo(file_path)
                    if isinstance(file_content, str):
                        file_content = file_content.encode('utf-8')
                    info.size = len(file_content)
                    tar.addfile(info, io.BytesIO(file_content))

        if dst is None:
            dst = "/"  # self.project_dir

        self.container.put_archive(dst.rstrip("/") + "/", tar_stream.getvalue())
    
    def run_command(self, command, workdir="/"):
        """Run a shell command in the container"""
        # print(f"Running command: {command}")
        # print(f"Container status before exec_run: {self.container.status}")
        
        if self.container.status != "running":
            print("Container is not running. Trying to start it again.")
            self.ensure_container_running()
        if self.verbose:
            print("ISOLATE: exec", command)
        
        result = self.container.exec_run(command, workdir=workdir)
        
        if self.verbose:
            print(f"ISOLATE: exec status={'OK' if result[1] == 0 else result[1]}")
        
        # print(f"Container status after exec_run: {self.container.status}")
        
        return result.output.decode("utf-8"), result.exit_code

    def get_file(self, file_path):
        """Retrieve a file from the container"""
        bits, _ = self.container.get_archive(file_path)
        return bits.decode("utf-8")

    def cleanup(self):
        """Clean up the container"""
        if hasattr(self, "container"):
            try:
                self.container.remove(force=True)
            except Exception as e:
                print(f"Error during cleanup: {e}")

    def __del__(self):
        self.cleanup()


if __name__ == "__main__":
    docker_env = DockerEnv()

    # Create a sample Python file
    python_code = "print('Hello, World!')"
    python_file = "test_python.py"

    # Write the Python code to a temporary file
    with open(python_file, "w") as f:
        f.write(python_code)
        f.flush()

    # Copy the Python file into the Docker environment
    docker_env.copy_files([python_file])

    # Run the Python file in the Docker environment
    result = docker_env.run_command(f"python {python_file}")

    # print(result)

    # Check that the output is correct
    assert result[0].strip() == "Hello, World!"

    print("SELF-TEST PASSED [OK]")

    # Clean up
    os.remove(python_file)

    del docker_env
