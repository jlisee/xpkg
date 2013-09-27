all: toola toolb

toola:
	g++ -o toola toola.cpp ${CPPFLAGS} ${LDFLAGS}

toolb:
	g++ -o toolb toolb.cpp ${CPPFLAGS} ${LDFLAGS}

install: toola toolb
	mkdir -p ${DESTDIR}/bin
	install -m 744 toola ${DESTDIR}/bin
	install -m 744 toolb ${DESTDIR}/bin

clean:
	rm -f toola toolb

distclean: clean
	rm -f Makefile
