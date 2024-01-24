PROG=		something

all:		something
		install -m 755 ${PROG}.sh ${PROG}

install:	all
		mkdir -p ${DESTDIR}/usr/bin
		install -o root -g root -m 755 ${PROG} ${DESTDIR}/usr/bin/
		mkdir -p ${DESTDIR}/usr/share/doc/${PROG}
		install -o root -g root -m 644 README ${DESTDIR}/usr/share/doc/${PROG}/
		find -- '${DESTDIR}/'

clean:
		rm -f -- something
