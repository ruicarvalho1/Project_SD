import time
import sys
import select
from .auction_utils import NEEDS_REFRESH


def input_with_timeout(prompt, timeout=5.0):
    print(prompt, end='', flush=True)

    if sys.platform == "win32":
        import msvcrt
        start_time = time.time()
        user_input = ""

        while True:
            if msvcrt.kbhit():
                char = msvcrt.getwche()
                if char == "\r":
                    print()
                    return user_input
                elif char == "\b":
                    if user_input:
                        user_input = user_input[:-1]
                        print("\b \b", end="", flush=True)
                else:
                    user_input += char

            global NEEDS_REFRESH
            if NEEDS_REFRESH:
                print()
                return None

            if time.time() - start_time > timeout:
                print()
                return None

            time.sleep(0.1)

    else:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if ready:
            return sys.stdin.readline().strip()
        return None
