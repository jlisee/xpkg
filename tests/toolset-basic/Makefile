all:
	$(CC) basic.c -o basic $(LDFLAGS) -static

install:
	mkdir -p ${DESTDIR}/bin
	install -m 744 basic ${DESTDIR}/bin

clean:
	rm -f basic
