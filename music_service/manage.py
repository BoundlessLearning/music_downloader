#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_service.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # 默认监听 127.0.0.1，端口从环境变量中获取，默认 16333
    port = os.environ.get("DJANGO_PORT", "16333")
    sys.argv = ["manage.py", "runserver", f"0.0.0.0:{port}"]
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
