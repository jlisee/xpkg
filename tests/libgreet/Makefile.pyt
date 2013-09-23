all: libgreet.so

greet.o:
	g++ -fPIC -c greet.cpp ${EXTRA_FLAGS} -DINSTALL_DIR="${DESTDIR}"

libgreet.so: greet.o
	g++ -shared -o libgreet.so.1 greet.o

install: libgreet.so.1
	mkdir -p ${DESTDIR}/lib
	install -m 744 libgreet.so.1 ${DESTDIR}/lib

	ln -s libgreet.so.1 ${DESTDIR}/lib/libgreet.so

	mkdir -p ${DESTDIR}/include/greet
	install -m 644 greet.h ${DESTDIR}/include/greet

	mkdir -p ${DESTDIR}/share/libgreet
	install -m 644 settings.conf ${DESTDIR}/share/libgreet

clean:
	rm -f greet.o libgreet.so

distclean: clean
	rm -f Makefile settings.conf
