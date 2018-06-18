import os


def is_raspberry_pi():
    if os.uname().machine.startswith('armv'):
        return True
    return False
