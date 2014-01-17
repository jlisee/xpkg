all:
	gcc commands.c -o commands $(LDFLAGS)

install:
	mkdir -p ${DESTDIR}/bin
	install -m 744 commands ${DESTDIR}/bin

clean:
	rm -f basic
