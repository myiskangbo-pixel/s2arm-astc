# Texture sub-module unit tests (seconds): make run
CFLAGS = -O2 -g -Wall -Wextra
t_tex: t_tex.c ../nvn_deswizzle.c ../nvn_deswizzle.h ../../nvn/nvn_tex.c ../../nvn/nvn_tex.h
	clang $(CFLAGS) -o $@ t_tex.c ../nvn_deswizzle.c ../../nvn/nvn_tex.c -lm
t_fmt_mtl: t_fmt_mtl.m ../nvn_fmt_mtl.c ../nvn_fmt_mtl.h ../../nvn/nvn_fmt_expand.c ../../nvn/nvn_fmt_expand.h
	clang $(CFLAGS) -fobjc-arc -o $@ t_fmt_mtl.m ../nvn_fmt_mtl.c ../../nvn/nvn_fmt_expand.c -framework Metal -framework Foundation
t_bc_soft: t_bc_soft.c ../nvn_bc_soft.c ../nvn_bc_soft.h ../nvn_bc_tables.h ../nvn_fmt_mtl.c ../nvn_fmt_mtl.h ../../nvn/nvn_fmt_expand.c ../../nvn/nvn_fmt_info.h
	clang $(CFLAGS) -o $@ t_bc_soft.c ../nvn_bc_soft.c ../nvn_fmt_mtl.c ../../nvn/nvn_fmt_expand.c

t_tex_layout: t_tex_layout.c ../../nvn/nvn_tex.c ../../nvn/nvn_tex.h
	clang $(CFLAGS) -o $@ t_tex_layout.c ../../nvn/nvn_tex.c
run: t_tex t_fmt_mtl t_tex_layout t_bc_soft
	./t_fmt_mtl && ./t_tex && ./t_tex_layout && ./t_bc_soft
.PHONY: run
