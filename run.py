import os
import subprocess
import sys
import argparse
import threading

def print_output(pipe):
    for line in iter(pipe.readline, ''):
        print(line, end='')

def main():
    # Set up argparse
    parser = argparse.ArgumentParser(description='Run a Flask app with a specified database name.')
    parser.add_argument('database_name', type=str, help='The name of the database to use')
    args = parser.parse_args()

    venv_path = os.path.abspath('./venv')  # Use absolute path for venv
    script_path = os.path.abspath('./main.py')  # Use absolute path for script

    try:
        if sys.platform == 'win32':
            activate_script = os.path.join(venv_path, 'Scripts', 'activate.bat')  # Use activate.bat for Windows
            # Prepare the command to activate the environment and run the script
            command = f'cmd /c "{activate_script} && python {script_path}"'
        else:
            activate_script = os.path.join(venv_path, 'bin', 'activate')
            # Prepare the command to activate the environment and run the script
            command = f'source "{activate_script}" && python "{script_path}"'

        # Set the database name as an environment variable
        env = os.environ.copy()
        env['DATABASE_NAME'] = args.database_name
        env['PYTHONUNBUFFERED'] = '1'  # Disable buffering

        # Debug: print the command to be executed
        print(f'Executing command: {command}')

        # Run the command with the modified environment and capture output in real-time
        process = subprocess.Popen(command, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Create threads to print output and error streams
        stdout_thread = threading.Thread(target=print_output, args=(process.stdout,))
        stderr_thread = threading.Thread(target=print_output, args=(process.stderr,))

        stdout_thread.start()
        stderr_thread.start()

        # Wait for the process to complete and the threads to finish
        process.wait()
        stdout_thread.join()
        stderr_thread.join()

        if process.returncode != 0:
            print(f'Command exited with code: {process.returncode}')
    except subprocess.CalledProcessError as e:
        print(f'Error occurred: {e}')  # Print error message if command fails
    except KeyboardInterrupt:
        print('Process interrupted by user')
        sys.exit()

if __name__ == '__main__':
    main()
