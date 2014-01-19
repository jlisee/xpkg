all:
	gcc env_command.c -o env_command $(LDFLAGS) $(EXTRA_FLAGS)

install:
	mkdir -p ${DESTDIR}/bin
	install -m 744 env_command ${DESTDIR}/bin

clean:
	rm -f env_command
