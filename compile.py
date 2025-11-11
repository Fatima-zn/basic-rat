import PyInstaller.__main__
import os
import platform


def compile_client():
    system = platform.system()

    if system == "Windows":
        PyInstaller.__main__.run([
            "client.py",
            "--onefile",
            "--noconsole",
            "--name=Update",
            "--clean"
        ])

    else:
        PyInstaller.__main__.run([
            "client.py",
            "--onefile",
            "--name=system-update-manager",
            "--clean"
        ])


if __name__ == "__main__":
    compile_client()