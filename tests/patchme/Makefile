all:
	gcc main.c -o patchme $(CFLAGS) $(LDFLAGS)

install:
	mkdir -p ${DESTDIR}/bin
	install -m 744 patchme ${DESTDIR}/bin

clean:
	rm -f patchme
