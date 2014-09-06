import sys


def greet():
    print('Hello, world!')


def main(argv = None):
    if argv is None:
        argv = sys.argv

    greet()


if __name__ == '__main__':
    sys.exit(main())
