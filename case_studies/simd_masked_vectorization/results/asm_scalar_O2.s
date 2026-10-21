	.file	"kernel.c"
	.text
	.p2align 4
	.globl	kernel
	.type	kernel, @function
kernel:
.LFB0:
	.cfi_startproc
	endbr64
	movslq	%edx, %rcx
	xorl	%eax, %eax
	pxor	%xmm1, %xmm1
	salq	$2, %rcx
	testl	%edx, %edx
	jg	.L5
	ret
	.p2align 4,,10
	.p2align 3
.L11:
	pxor	%xmm0, %xmm0
	movss	%xmm0, (%rsi,%rax)
	addq	$4, %rax
	cmpq	%rax, %rcx
	je	.L1
.L5:
	movss	(%rdi,%rax), %xmm0
	comiss	%xmm1, %xmm0
	jbe	.L11
	sqrtss	%xmm0, %xmm0
	movss	%xmm0, (%rsi,%rax)
	addq	$4, %rax
	cmpq	%rax, %rcx
	jne	.L5
.L1:
	ret
	.cfi_endproc
.LFE0:
	.size	kernel, .-kernel
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
	.section	.note.gnu.property,"a"
	.align 8
	.long	1f - 0f
	.long	4f - 1f
	.long	5
0:
	.string	"GNU"
1:
	.align 8
	.long	0xc0000002
	.long	3f - 2f
2:
	.long	0x3
3:
	.align 8
4:
