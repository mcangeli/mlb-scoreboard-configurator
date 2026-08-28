from .network import maintain_hotspot

def main():
    ok, message = maintain_hotspot()
    print(message)
    raise SystemExit(0 if ok else 1)
