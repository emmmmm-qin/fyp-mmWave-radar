"""Check firmware-produced frames with the Windows viewer's real serial parser."""
import argparse
from pathlib import Path
import subprocess
from protocol import LineReader


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('encoder', type=Path, help='native firmware test executable')
    args = parser.parse_args()
    output = subprocess.run([str(args.encoder.resolve()), '--emit-fixture'],
                            check=True, stdout=subprocess.PIPE).stdout
    reader = LineReader()
    packets = []
    for offset in range(0, len(output), 7):
        for item, error in reader.feed(output[offset:offset + 7]):
            if error:
                raise SystemExit(error)
            packets.append(item[0])
    expected = {'protocol': 'fyp-radar', 'v': 2, 'source': 'radar', 'seq': 42,
                't_ms': 5300, 'state': 'cloud', 'points': [[-1, 2, -1.5], [0, 0, 16383.5]]}
    if packets != [expected]:
        raise SystemExit('Firmware fixture did not deliver the expected frame and coordinates')
    print('PASS: firmware-to-viewer fixture, 2 synthetic points with expected coordinates and velocities')


if __name__ == '__main__':
    main()
