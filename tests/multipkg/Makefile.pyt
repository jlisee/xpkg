all: toola toolb libmulti.so

multilib.o:
	g++ -fPIC -c multilib.cpp

libmulti.so: multilib.o
	g++ -shared -o libmulti.so multilib.o

toola: libmulti.so
	g++ -o toola toola.cpp -lmulti ${CPPFLAGS} ${LDFLAGS} -L.

toolb: libmulti.so
	g++ -o toolb toolb.cpp -lmulti ${CPPFLAGS} ${LDFLAGS} -L.

install: toola toolb libmulti.so
	mkdir -p ${DESTDIR}/lib
	install -m 744 libmulti.so ${DESTDIR}/lib

	mkdir -p ${DESTDIR}/include/multi
	install -m 644 multilib.h ${DESTDIR}/include/multi

	mkdir -p ${DESTDIR}/bin
	install -m 744 toola ${DESTDIR}/bin
	install -m 744 toolb ${DESTDIR}/bin

clean:
	rm -f toola toolb *.o libmulti.so

distclean: clean
	rm -f Makefile
