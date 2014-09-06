all:
	mkdir build
	cp greet.py build

install:
	mkdir -p ${DESTDIR}/lib/python
	install -m 644 build/greet.py ${DESTDIR}/lib/python
	python -m py_compile ${DESTDIR}/lib/python/greet.py

clean:
	rm -f build
