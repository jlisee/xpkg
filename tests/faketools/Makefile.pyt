all:
	cp configure fake-configure

install:
	mkdir -p ${DESTDIR}/bin
	install -m 744 fake-configure ${DESTDIR}/bin

clean:
	rm -f fake-configure

distclean: clean
	rm -f Makefile
