include $(top_srcdir)/common.mk

bin_PROGRAMS = epimetheus
DEFS = -DEPIMETHEUS
LIBS = -L$(FDLIBM_DIR) -lfdm
epimetheus_DEPENDENCIES = $(LIBFDLIBM)
epimetheus_SOURCES =  \
	bytecodecontainer.cpp \
	epimetheus.cpp \
	exception.cpp \
	formatter.cpp \
	hash.cpp \
	js2array.cpp \
	js2boolean.cpp \
	js2date.cpp \
	js2engine.cpp \
	js2error.cpp \
	js2eval.cpp \
	js2function.cpp \
	js2math.cpp \
	js2metadata.cpp \
	js2number.cpp \
	js2regexp.cpp \
	js2string.cpp \
	lexer.cpp \
	mem.cpp \
	numerics.cpp \
	parser.cpp \
	prmjtime.cpp \
	reader.cpp \
        regexpwrapper.cpp \
	strings.cpp \
	token.cpp \
	utilities.cpp \
	world.cpp
