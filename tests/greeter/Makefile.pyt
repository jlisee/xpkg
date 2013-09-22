all: greeter

greeter.o:
	g++ -fPIC -c greeter.cpp ${CPPFLAGS}

greeter: greeter.o
	g++ -o greeter greeter.o -lgreet ${LDFLAGS}

install: greeter
	mkdir -p ${DESTDIR}/bin
	install -m 744 greeter ${DESTDIR}/bin

clean:
	rm -f greeter greeter.o

distclean: clean
	rm -f Makefile
