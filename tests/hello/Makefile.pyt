make:
	g++ hello.cpp -o hello

install:
	mkdir -p ${DESTDIR}/bin
	install -m 744 hello ${DESTDIR}/bin

clean:
	rm -f hello

distclean: clean
	rm -f Makefile
