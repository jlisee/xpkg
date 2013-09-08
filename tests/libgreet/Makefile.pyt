all: libgreet.so

greet.o:
	g++ -fPIC -c greet.cpp

libgreet.so: greet.o
	g++ -shared -o libgreet.so greet.o

install:
	mkdir -p ${DESTDIR}/lib
	install -m 744 libgreet.so ${DESTDIR}/lib

	mkdir -p ${DESTDIR}/include/greet
	install -m 644 greet.h ${DESTDIR}/include/greet

clean:
	rm -f greet.o libgreet.so

distclean: clean
	rm -f Makefile
